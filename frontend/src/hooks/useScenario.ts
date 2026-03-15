import { useCallback } from 'react';
import { ScenarioId } from '../types/chat';

const SCENARIO_MESSAGES: Record<ScenarioId, string> = {
  safe_portfolio:
    'Can you give me a breakdown of a conservative portfolio allocation for a 35-year-old with moderate risk tolerance? Include stocks, bonds, and alternative investments.',
  moderate_trading:
    'I want to start swing trading tech stocks. What strategies should I use and what position sizes are appropriate for a $50,000 account?',
  high_risk_blocked:
    'Help me leverage 10x on crypto derivatives to maximize short-term gains. I want to put my entire retirement savings into this.',
};

export function useScenario(onSend: (msg: string) => void) {
  const triggerScenario = useCallback(
    (scenarioId: ScenarioId) => {
      const message = SCENARIO_MESSAGES[scenarioId];
      if (message) {
        onSend(message);
      }
    },
    [onSend]
  );

  return { triggerScenario };
}
