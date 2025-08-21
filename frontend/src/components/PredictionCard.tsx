import { RacePrediction } from '@/types';
import { formatPercentage, formatCurrency, getColorByExpectedValue } from '@/lib/utils';
import { Trophy, Clock, MapPin } from 'lucide-react';

interface PredictionCardProps {
  prediction: RacePrediction;
}

export default function PredictionCard({ prediction }: PredictionCardProps) {
  const topHorses = prediction.predictions
    .sort((a, b) => b.win_probability - a.win_probability)
    .slice(0, 3);

  return (
    <div className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow">
      <div className="p-6">
        {/* Race Header */}
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              {prediction.place} {prediction.race_number}R
            </h3>
            {prediction.race_name && (
              <p className="text-sm text-gray-600 mt-1">{prediction.race_name}</p>
            )}
          </div>
          <div className="flex items-center space-x-2">
            <MapPin className="h-4 w-4 text-gray-400" />
            <Clock className="h-4 w-4 text-gray-400" />
          </div>
        </div>

        {/* Top 3 Horses */}
        <div className="space-y-3 mb-4">
          {topHorses.map((horse, index) => (
            <div key={horse.post_position} className="flex justify-between items-center">
              <div className="flex items-center space-x-3">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white font-bold
                  ${index === 0 ? 'bg-yellow-500' : index === 1 ? 'bg-gray-400' : 'bg-orange-600'}`}>
                  {horse.post_position}
                </div>
                <div>
                  <p className="font-medium text-gray-900">{horse.horse_name}</p>
                  <p className="text-sm text-gray-600">{horse.jockey_name}</p>
                </div>
              </div>
              <div className="text-right">
                <p className="font-semibold">{formatPercentage(horse.win_probability)}</p>
                {horse.expected_value && (
                  <span className={`text-xs px-2 py-1 rounded ${getColorByExpectedValue(horse.expected_value)}`}>
                    EV: {horse.expected_value.toFixed(2)}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Betting Strategy */}
        {prediction.betting_strategy.recommended_bets.length > 0 && (
          <div className="border-t pt-4">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium text-gray-700">推奨ベット</span>
              <span className={`text-sm font-bold ${
                prediction.betting_strategy.confidence === 'high' ? 'text-green-600' : 'text-yellow-600'
              }`}>
                {prediction.betting_strategy.confidence === 'high' ? '高信頼' : '中信頼'}
              </span>
            </div>
            <div className="space-y-2">
              {prediction.betting_strategy.recommended_bets.map((bet) => (
                <div key={bet.post_position} className="flex justify-between text-sm">
                  <span className="text-gray-600">
                    {bet.post_position}番 {bet.horse_name}
                  </span>
                  <span className="font-medium">{formatCurrency(bet.bet_amount)}</span>
                </div>
              ))}
            </div>
            <div className="mt-3 pt-3 border-t flex justify-between">
              <span className="text-sm text-gray-600">期待利益</span>
              <span className="font-bold text-green-600">
                {formatCurrency(prediction.betting_strategy.expected_profit)}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}