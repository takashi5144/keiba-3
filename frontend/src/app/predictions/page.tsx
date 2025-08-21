'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { format } from 'date-fns';
import { Search, Calendar, ChevronRight } from 'lucide-react';
import { api } from '@/lib/api';
import { RacePrediction } from '@/types';
import { formatPercentage, formatCurrency, getColorByProbability } from '@/lib/utils';

export default function PredictionsPage() {
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [selectedPlace, setSelectedPlace] = useState<string>('');
  const [selectedRace, setSelectedRace] = useState<RacePrediction | null>(null);

  // Fetch predictions for selected date
  const { data: batchPredictions, isLoading, refetch } = useQuery({
    queryKey: ['predictions', 'batch', selectedDate, selectedPlace],
    queryFn: async () => {
      const response = await api.prediction.predictBatch({
        target_date: format(selectedDate, 'yyyy-MM-dd'),
        place: selectedPlace || undefined,
      });
      return response.data;
    },
    enabled: false,
  });

  // Handle search
  const handleSearch = () => {
    refetch();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <h1 className="text-3xl font-bold text-gray-900">レース予測</h1>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Search Section */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                日付
              </label>
              <div className="relative">
                <input
                  type="date"
                  value={format(selectedDate, 'yyyy-MM-dd')}
                  onChange={(e) => setSelectedDate(new Date(e.target.value))}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md"
                />
                <Calendar className="absolute right-3 top-2.5 h-5 w-5 text-gray-400" />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                競馬場
              </label>
              <select
                value={selectedPlace}
                onChange={(e) => setSelectedPlace(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-md"
              >
                <option value="">全競馬場</option>
                <option value="東京">東京</option>
                <option value="中山">中山</option>
                <option value="阪神">阪神</option>
                <option value="京都">京都</option>
                <option value="小倉">小倉</option>
                <option value="新潟">新潟</option>
                <option value="福島">福島</option>
                <option value="中京">中京</option>
                <option value="札幌">札幌</option>
                <option value="函館">函館</option>
              </select>
            </div>

            <div className="flex items-end">
              <button
                onClick={handleSearch}
                disabled={isLoading}
                className="w-full px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 flex items-center justify-center"
              >
                {isLoading ? (
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                ) : (
                  <>
                    <Search className="h-5 w-5 mr-2" />
                    予測実行
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Results Section */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Race List */}
          <div className="lg:col-span-1">
            <h2 className="text-xl font-bold text-gray-900 mb-4">レース一覧</h2>
            
            {batchPredictions?.predictions && batchPredictions.predictions.length > 0 ? (
              <div className="space-y-3">
                {batchPredictions.predictions.map((prediction: RacePrediction) => (
                  <div
                    key={prediction.race_id}
                    onClick={() => setSelectedRace(prediction)}
                    className={`bg-white rounded-lg shadow p-4 cursor-pointer hover:shadow-md transition-shadow ${
                      selectedRace?.race_id === prediction.race_id ? 'ring-2 ring-blue-500' : ''
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="font-semibold text-gray-900">
                          {prediction.place} {prediction.race_number}R
                        </p>
                        {prediction.race_name && (
                          <p className="text-sm text-gray-600 mt-1">{prediction.race_name}</p>
                        )}
                        <p className="text-xs text-gray-500 mt-2">
                          出走: {prediction.num_horses}頭
                        </p>
                      </div>
                      <ChevronRight className="h-5 w-5 text-gray-400" />
                    </div>
                    
                    {prediction.betting_strategy.recommended_bets.length > 0 && (
                      <div className="mt-3 pt-3 border-t">
                        <p className="text-sm text-green-600 font-medium">
                          推奨ベット: {prediction.betting_strategy.recommended_bets.length}点
                        </p>
                        <p className="text-xs text-gray-600 mt-1">
                          期待利益: {formatCurrency(prediction.betting_strategy.expected_profit)}
                        </p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow p-6 text-center text-gray-500">
                レースを検索してください
              </div>
            )}
          </div>

          {/* Race Details */}
          <div className="lg:col-span-2">
            <h2 className="text-xl font-bold text-gray-900 mb-4">予測詳細</h2>
            
            {selectedRace ? (
              <div className="bg-white rounded-lg shadow">
                {/* Race Header */}
                <div className="p-6 border-b">
                  <h3 className="text-lg font-semibold text-gray-900">
                    {selectedRace.place} {selectedRace.race_number}R
                  </h3>
                  {selectedRace.race_name && (
                    <p className="text-gray-600 mt-1">{selectedRace.race_name}</p>
                  )}
                  <p className="text-sm text-gray-500 mt-2">
                    {format(new Date(selectedRace.race_date), 'yyyy年MM月dd日')} · {selectedRace.num_horses}頭立て
                  </p>
                </div>

                {/* Predictions Table */}
                <div className="p-6">
                  <h4 className="font-medium text-gray-900 mb-4">出走馬予測</h4>
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead>
                        <tr>
                          <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            枠番
                          </th>
                          <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            馬名
                          </th>
                          <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            騎手
                          </th>
                          <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            勝率
                          </th>
                          <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            オッズ
                          </th>
                          <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            期待値
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        {selectedRace.predictions
                          .sort((a, b) => b.win_probability - a.win_probability)
                          .map((horse) => (
                            <tr key={horse.post_position}>
                              <td className="px-3 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                {horse.post_position}
                              </td>
                              <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-900">
                                {horse.horse_name}
                              </td>
                              <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-600">
                                {horse.jockey_name}
                              </td>
                              <td className={`px-3 py-4 whitespace-nowrap text-sm font-semibold ${getColorByProbability(horse.win_probability)}`}>
                                {formatPercentage(horse.win_probability)}
                              </td>
                              <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-900">
                                {horse.odds ? horse.odds.toFixed(1) : '-'}
                              </td>
                              <td className="px-3 py-4 whitespace-nowrap text-sm">
                                {horse.expected_value ? (
                                  <span className={`px-2 py-1 rounded ${
                                    horse.expected_value >= 1.2 ? 'bg-green-100 text-green-800' :
                                    horse.expected_value >= 1.0 ? 'bg-yellow-100 text-yellow-800' :
                                    'bg-gray-100 text-gray-800'
                                  }`}>
                                    {horse.expected_value.toFixed(2)}
                                  </span>
                                ) : '-'}
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Betting Strategy */}
                {selectedRace.betting_strategy.recommended_bets.length > 0 && (
                  <div className="p-6 border-t bg-gray-50">
                    <h4 className="font-medium text-gray-900 mb-4">推奨ベット戦略</h4>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-sm text-gray-600">戦略</p>
                        <p className="font-semibold">{selectedRace.betting_strategy.strategy}</p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600">信頼度</p>
                        <p className="font-semibold">{selectedRace.betting_strategy.confidence}</p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600">投資額</p>
                        <p className="font-semibold">{formatCurrency(selectedRace.betting_strategy.total_bet_amount)}</p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600">期待利益</p>
                        <p className="font-semibold text-green-600">
                          {formatCurrency(selectedRace.betting_strategy.expected_profit)}
                        </p>
                      </div>
                    </div>
                    
                    <div className="mt-4">
                      <p className="text-sm text-gray-600 mb-2">推奨馬券</p>
                      <div className="space-y-2">
                        {selectedRace.betting_strategy.recommended_bets.map((bet) => (
                          <div key={bet.post_position} className="flex justify-between bg-white rounded p-3">
                            <span className="text-sm">
                              {bet.post_position}番 {bet.horse_name}
                            </span>
                            <span className="font-semibold text-sm">
                              {formatCurrency(bet.bet_amount)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow p-12 text-center text-gray-500">
                レースを選択してください
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}