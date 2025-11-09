from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import AsyncGenerator, Dict, Optional

from agno.agent import Agent
from loguru import logger

from valuecell.core.agent.responses import streaming
from valuecell.core.types import BaseAgent, StreamResponse
from valuecell.server.services import strategy_persistence
from valuecell.adapters.models.factory import create_model

from .constants import DEFAULT_AGENT_MODEL, DEFAULT_INITIAL_CAPITAL
from .models import (
    ComponentType,
    StrategyStatus,
    StrategyStatusContent,
    UserRequest,
)
from .runtime import create_strategy_runtime_async


class StrategyAgent(BaseAgent):
    """Top-level Strategy Agent integrating the decision coordinator."""

    def __init__(self):
        super().__init__()
        try:
            parser_model = create_model()
            self.parser_agent = Agent(
                model=parser_model,
                output_schema=UserRequest,
                markdown=False,
            )
        except Exception:
            self.parser_agent = None

    async def _wait_until_marked_running(
        self, strategy_id: str, timeout_s: int = 300
    ) -> None:
        """Wait until persistence marks the strategy as running or timeout.

        This helper logs progress and returns when either the strategy is running
        or the timeout elapses. It swallows exceptions from the persistence layer
        to avoid bubbling nested try/except into `stream`.
        """
        since = datetime.now()
        try:
            while not strategy_persistence.strategy_running(strategy_id):
                if (datetime.now() - since).total_seconds() > timeout_s:
                    logger.error(
                        "Timeout waiting for strategy_id={} to be marked as running",
                        strategy_id,
                    )
                    break

                await asyncio.sleep(1)
                logger.info(
                    "Waiting for strategy_id={} to be marked as running", strategy_id
                )
        except Exception:
            # Avoid raising from persistence checks; we still proceed to start the runtime.
            logger.exception(
                "Error while waiting for strategy {} to be marked running", strategy_id
            )

    def _persist_initial_state(self, runtime, strategy_id: str) -> None:
        """Persist initial portfolio snapshot and strategy summary.

        This helper captures and logs any errors internally so callers don't need
        additional try/except nesting.
        """
        try:
            initial_portfolio = runtime.coordinator._portfolio_service.get_view()
            try:
                initial_portfolio.strategy_id = strategy_id
            except Exception:
                pass

            ok = strategy_persistence.persist_portfolio_view(initial_portfolio)
            if ok:
                logger.info(
                    "Persisted initial portfolio view for strategy={}", strategy_id
                )

            timestamp_ms = int(runtime.coordinator._clock().timestamp() * 1000)
            initial_summary = runtime.coordinator._build_summary(timestamp_ms, [])
            ok = strategy_persistence.persist_strategy_summary(initial_summary)
            if ok:
                logger.info(
                    "Persisted initial strategy summary for strategy={}", strategy_id
                )
        except Exception:
            logger.exception(
                "Failed to persist initial portfolio/summary for {}", strategy_id
            )

    def _persist_cycle_results(self, strategy_id: str, result) -> None:
        """Persist trades, portfolio view and strategy summary for a cycle.

        Errors are logged but not raised to keep the decision loop resilient.
        """
        try:
            for trade in result.trades:
                item = strategy_persistence.persist_trade_history(strategy_id, trade)
                if item:
                    logger.info(
                        "Persisted trade {} for strategy={}",
                        getattr(trade, "trade_id", None),
                        strategy_id,
                    )

            ok = strategy_persistence.persist_portfolio_view(result.portfolio_view)
            if ok:
                logger.info("Persisted portfolio view for strategy={}", strategy_id)

            ok = strategy_persistence.persist_strategy_summary(result.strategy_summary)
            if ok:
                logger.info("Persisted strategy summary for strategy={}", strategy_id)
        except Exception:
            logger.exception("Error persisting cycle results for {}", strategy_id)

    async def _parse_strategy_request(self, query: str) -> UserRequest:
        if not self.parser_agent:
            raise ValueError("Parser agent not initialized")
        parse_prompt = f'Parse the user query and extract strategy configuration: "{query}". Extract symbols (format: SYMBOL-USD), initial_capital (default: {DEFAULT_INITIAL_CAPITAL}), and other UserRequest fields.'
        response = await self.parser_agent.arun(parse_prompt)
        return response.content

    async def stream(
        self,
        query: str,
        conversation_id: str,
        task_id: str,
        dependencies: Optional[Dict] = None,
    ) -> AsyncGenerator[StreamResponse, None]:
        try:
            request = UserRequest.model_validate_json(query)
        except (ValueError, json.JSONDecodeError):
            request = await self._parse_strategy_request(query)

        runtime = await create_strategy_runtime_async(request)
        strategy_id = runtime.strategy_id
        logger.info(
            "Created runtime for strategy_id={} conversation={} task={}",
            strategy_id,
            conversation_id,
            task_id,
        )
        initial_payload = StrategyStatusContent(
            strategy_id=strategy_id,
            status=StrategyStatus.RUNNING,
        )
        yield streaming.component_generator(
            content=initial_payload.model_dump_json(),
            component_type=ComponentType.STATUS.value,
        )

        # Wait until strategy is marked as running in persistence layer
        await self._wait_until_marked_running(strategy_id)

        try:
            logger.info("Starting decision loop for strategy_id={}", strategy_id)
            # Persist initial portfolio snapshot and strategy summary before entering the loop
            self._persist_initial_state(runtime, strategy_id)
            while True:
                if not strategy_persistence.strategy_running(strategy_id):
                    logger.info(
                        "Strategy_id={} is no longer running, exiting decision loop",
                        strategy_id,
                    )
                    break

                result = await runtime.run_cycle()
                logger.info(
                    "Run cycle completed for strategy={} trades_count={}",
                    strategy_id,
                    len(result.trades),
                )
                # Persist and stream cycle results (trades, portfolio, summary)
                self._persist_cycle_results(strategy_id, result)

                logger.info(
                    "Waiting for next decision cycle for strategy_id={}, interval={}seconds",
                    strategy_id,
                    request.trading_config.decide_interval,
                )
                await asyncio.sleep(request.trading_config.decide_interval)

        except asyncio.CancelledError:
            # Ensure strategy is marked stopped on cancellation
            try:
                strategy_persistence.mark_strategy_stopped(strategy_id)
                logger.info(
                    "Marked strategy {} as stopped due to cancellation", strategy_id
                )
            except Exception:
                logger.exception(
                    "Failed to mark strategy stopped for {} on cancellation",
                    strategy_id,
                )
            raise
        except Exception as err:  # noqa: BLE001
            logger.exception("StrategyAgent stream failed: {}", err)
            yield streaming.message_chunk(f"StrategyAgent error: {err}")
        finally:
            # Always mark strategy as stopped when stream ends for any reason
            try:
                strategy_persistence.mark_strategy_stopped(strategy_id)
                logger.info("Marked strategy {} as stopped in finalizer", strategy_id)
            except Exception:
                logger.exception(
                    "Failed to mark strategy stopped for {} in finalizer", strategy_id
                )
            yield streaming.done()
