/**
 * @file The `Leaderboard` component displays a ranked list of oracle providers.
 * @description This component fetches performance data for all registered providers from the Canton ledger
 * and ranks them based on their accuracy and uptime. It provides a real-time, transparent
 * view of the health and reliability of the oracle network.
 *
 * The component uses the `@c7/react` library's `useStreamQueries` hook to subscribe to a stream
 * of `Performance` contracts from the ledger.
 */
import React from 'react';
import { useStreamQueries } from '@c7/react';
// This import assumes the DPM project name is 'canton-oracle-network' and the version is '0.1.0'.
// The path corresponds to the Daml module `Oracle.Provider.Performance`.
import { Performance } from '@daml.js/canton-oracle-network-0.1.0/lib/Oracle/Provider/Performance';

/**
 * A utility type for the processed leaderboard data for easier handling in the component.
 */
type LeaderboardEntry = {
  provider: string;
  displayName: string;
  accuracyScore: number;
  uptime: number;
  totalUpdates: number;
};

/**
 * Formats a ratio as a percentage string with two decimal places.
 * @param {number} ratio - The ratio to format (e.g., 0.995).
 * @returns {string} The formatted percentage string (e.g., "99.50%").
 */
const formatPercentage = (ratio: number): string => `${(ratio * 100).toFixed(2)}%`;

/**
 * Renders an informational panel for when the leaderboard is in a loading or empty state.
 * @param {object} props - The component props.
 * @param {string} props.message - The message to display.
 * @returns {React.ReactElement} The rendered panel.
 */
const InfoPanel: React.FC<{ message: string }> = ({ message }) => (
  <div className="flex items-center justify-center p-12 bg-gray-800/50 rounded-lg">
    <p className="text-gray-400">{message}</p>
  </div>
);


/**
 * The main Leaderboard component.
 * It fetches, processes, and displays oracle provider performance data in a ranked table.
 */
export const Leaderboard: React.FC = () => {
  const { contracts: performanceContracts, loading } = useStreamQueries(Performance);

  const leaderboardData = React.useMemo<LeaderboardEntry[]>(() => {
    if (!performanceContracts) return [];

    const processed = performanceContracts.map(c => {
      const totalUpdates = parseInt(c.payload.totalUpdates, 10);
      const successfulUpdates = parseInt(c.payload.successfulUpdates, 10);

      const uptime = totalUpdates > 0
        ? successfulUpdates / totalUpdates
        : 0;

      return {
        provider: c.payload.provider,
        displayName: c.payload.displayName,
        accuracyScore: parseFloat(c.payload.accuracyScore),
        uptime: uptime,
        totalUpdates: totalUpdates
      };
    });

    // Sort providers. Primary sort key: accuracy score (lower is better).
    // Secondary sort key: uptime (higher is better).
    processed.sort((a, b) => {
      if (a.accuracyScore !== b.accuracyScore) {
        return a.accuracyScore - b.accuracyScore;
      }
      return b.uptime - a.uptime;
    });

    return processed;
  }, [performanceContracts]);

  const renderTable = () => (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-700">
        <thead className="bg-gray-800">
          <tr>
            <th scope="col" className="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-300 sm:pl-6">Rank</th>
            <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-300">Provider</th>
            <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-300">Accuracy Score</th>
            <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-300">Uptime</th>
            <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-300">Total Updates</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-800 bg-gray-900">
          {leaderboardData.map((provider, index) => (
            <tr key={provider.provider} className="hover:bg-gray-700/50 transition-colors duration-150">
              <td className="whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-white sm:pl-6">{index + 1}</td>
              <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-300">{provider.displayName}</td>
              <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-300 font-mono" title="Lower is better">{provider.accuracyScore.toFixed(8)}</td>
              <td className="whitespace-nowrap px-3 py-4 text-sm">
                <span className={
                  provider.uptime >= 0.99 ? 'text-green-400' :
                  provider.uptime > 0.95 ? 'text-yellow-400' :
                  'text-red-400'
                }>
                  {formatPercentage(provider.uptime)}
                </span>
              </td>
              <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-300 font-mono">{provider.totalUpdates.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return (
    <div className="bg-gray-900 text-white p-4 sm:p-6 lg:p-8 rounded-lg shadow-xl">
      <h2 className="text-2xl font-bold mb-6 text-gray-100">Provider Leaderboard</h2>
      { loading
          ? <InfoPanel message="Loading provider performance data..." />
          : leaderboardData.length === 0
          ? <InfoPanel message="No provider data available." />
          : renderTable()
      }
    </div>
  );
};

export default Leaderboard;