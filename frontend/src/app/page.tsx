'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import { Activity, TrendingUp, DollarSign, Award } from 'lucide-react';
import { api } from '@/lib/api';
import { formatCurrency, formatPercentage } from '@/lib/utils';
import PredictionCard from '@/components/PredictionCard';
import MetricsCard from '@/components/MetricsCard';
import ModelPerformance from '@/components/ModelPerformance';

export default function Dashboard() {
  const [selectedDate, setSelectedDate] = useState(new Date());

  // Fetch today's predictions
  const { data: predictions, isLoading: predictionsLoading } = useQuery({
    queryKey: ['predictions', 'today'],
    queryFn: async () => {
      const response = await api.prediction.predictToday({});
      return response.data;
    },
  });

  // Fetch available models
  const { data: models } = useQuery({
    queryKey: ['models'],
    queryFn: async () => {
      const response = await api.prediction.getModels();
      return response.data;
    },
  });

  // Calculate summary metrics
  const summaryMetrics = predictions?.summary || {
    total_races: 0,
    recommended_races: 0,
    total_expected_profit: 0,
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex justify-between items-center">
            <h1 className="text-3xl font-bold text-gray-900">
              競馬予測ダッシュボード
            </h1>
            <div className="flex items-center space-x-4">
              <input
                type="date"
                value={format(selectedDate, 'yyyy-MM-dd')}
                onChange={(e) => setSelectedDate(new Date(e.target.value))}
                className="px-4 py-2 border border-gray-300 rounded-md"
              />
              <span className="text-sm text-gray-600">
                {format(selectedDate, 'yyyy年MM月dd日')}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <MetricsCard
            title="本日のレース"
            value={summaryMetrics.total_races}
            icon={<Activity className="h-6 w-6" />}
            color="blue"
          />
          <MetricsCard
            title="推奨レース"
            value={summaryMetrics.recommended_races}
            icon={<Award className="h-6 w-6" />}
            color="green"
          />
          <MetricsCard
            title="期待利益"
            value={formatCurrency(summaryMetrics.total_expected_profit)}
            icon={<DollarSign className="h-6 w-6" />}
            color="yellow"
          />
          <MetricsCard
            title="モデル数"
            value={models?.length || 0}
            icon={<TrendingUp className="h-6 w-6" />}
            color="purple"
          />
        </div>

        {/* Predictions Section */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">
            本日の予測
          </h2>
          
          {predictionsLoading ? (
            <div className="flex justify-center items-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
          ) : predictions?.predictions?.length > 0 ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {predictions.predictions
                .filter((p: any) => p.betting_strategy.recommended_bets.length > 0)
                .slice(0, 6)
                .map((prediction: any) => (
                  <PredictionCard key={prediction.race_id} prediction={prediction} />
                ))}
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow p-6 text-center text-gray-500">
              本日の予測データがありません
            </div>
          )}
        </div>

        {/* Model Performance Section */}
        {models && models.length > 0 && (
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              モデル性能
            </h2>
            <ModelPerformance models={models} />
          </div>
        )}
      </main>
    </div>
  );
}
