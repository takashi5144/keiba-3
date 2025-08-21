import { Model } from '../types';
import { formatPercentage } from '../lib/utils';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface ModelPerformanceProps {
  models: Model[];
}

export default function ModelPerformance({ models }: ModelPerformanceProps) {
  // Prepare chart data
  const chartData = models.map((model) => ({
    name: model.model_name,
    accuracy: model.metrics.accuracy * 100,
    precision: model.metrics.precision * 100,
    recall: model.metrics.recall * 100,
    roc_auc: model.metrics.roc_auc * 100,
  }));

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Model List */}
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">モデル一覧</h3>
          <div className="space-y-3">
            {models.map((model) => (
              <div key={model.filename} className="border rounded-lg p-4">
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <p className="font-medium text-gray-900">{model.model_name}</p>
                    <p className="text-sm text-gray-600">Version: {model.version}</p>
                  </div>
                  {model.trained_at && (
                    <p className="text-xs text-gray-500">
                      {new Date(model.trained_at).toLocaleDateString('ja-JP')}
                    </p>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-2 mt-3">
                  <div>
                    <span className="text-xs text-gray-600">精度</span>
                    <p className="font-semibold">{formatPercentage(model.metrics.accuracy)}</p>
                  </div>
                  <div>
                    <span className="text-xs text-gray-600">AUC</span>
                    <p className="font-semibold">{formatPercentage(model.metrics.roc_auc)}</p>
                  </div>
                  {model.metrics.roi !== undefined && (
                    <div>
                      <span className="text-xs text-gray-600">ROI</span>
                      <p className="font-semibold text-green-600">
                        {formatPercentage(model.metrics.roi)}
                      </p>
                    </div>
                  )}
                  {model.metrics.win_rate !== undefined && (
                    <div>
                      <span className="text-xs text-gray-600">的中率</span>
                      <p className="font-semibold">{formatPercentage(model.metrics.win_rate)}</p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Performance Chart */}
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">性能比較</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip formatter={(value) => `${value}%`} />
              <Legend />
              <Line type="monotone" dataKey="accuracy" stroke="#3B82F6" name="精度" />
              <Line type="monotone" dataKey="precision" stroke="#10B981" name="適合率" />
              <Line type="monotone" dataKey="recall" stroke="#F59E0B" name="再現率" />
              <Line type="monotone" dataKey="roc_auc" stroke="#8B5CF6" name="AUC" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}