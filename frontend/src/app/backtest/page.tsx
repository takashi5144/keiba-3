'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { format, subMonths } from 'date-fns';
import { TrendingUp, TrendingDown, DollarSign, Target, Calendar, PlayCircle } from 'lucide-react';
import { api } from '@/lib/api-client';
import { BacktestResult } from '@/types';
import { formatCurrency, formatPercentage } from '@/lib/utils';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export default function BacktestPage() {
  const [startDate, setStartDate] = useState(format(subMonths(new Date(), 3), 'yyyy-MM-dd'));
  const [endDate, setEndDate] = useState(format(new Date(), 'yyyy-MM-dd'));
  const [initialBudget, setInitialBudget] = useState(100000);
  const [minExpectedValue, setMinExpectedValue] = useState(1.2);
  const [backtestResult, setBacktestResult] = useState<BacktestResult | null>(null);

  // Backtest mutation
  const backtestMutation = useMutation({
    mutationFn: async () => {
      const response = await api.prediction.backtest({
        start_date: startDate,
        end_date: endDate,
        initial_budget: initialBudget,
        min_expected_value: minExpectedValue,
      });
      return response.data;
    },
    onSuccess: (data) => {
      setBacktestResult(data);
    },
  });

  // Prepare chart data
  const chartData = backtestResult?.results_sample.map((result, index) => ({
    race: index + 1,
    budget: result.budget_after,
    profit: result.budget_after - initialBudget,
    bet: result.bet_amount,
    win: result.win ? result.bet_amount * result.odds : 0,
  })) || [];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <h1 className="text-3xl font-bold text-gray-900">バックテスト</h1>
          <p className="mt-2 text-gray-600">過去データを使用して戦略の性能を評価</p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Configuration Section */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-4">テスト設定</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                開始日
              </label>
              <div className="relative">
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md"
                />
                <Calendar className="absolute right-3 top-2.5 h-5 w-5 text-gray-400" />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                終了日
              </label>
              <div className="relative">
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md"
                />
                <Calendar className="absolute right-3 top-2.5 h-5 w-5 text-gray-400" />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                初期資金
              </label>
              <div className="relative">
                <input
                  type="number"
                  value={initialBudget}
                  onChange={(e) => setInitialBudget(Number(e.target.value))}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md"
                  step="10000"
                />
                <DollarSign className="absolute right-3 top-2.5 h-5 w-5 text-gray-400" />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                最小期待値
              </label>
              <input
                type="number"
                value={minExpectedValue}
                onChange={(e) => setMinExpectedValue(Number(e.target.value))}
                className="w-full px-4 py-2 border border-gray-300 rounded-md"
                step="0.1"
                min="1.0"
              />
            </div>
          </div>

          <button
            onClick={() => backtestMutation.mutate()}
            disabled={backtestMutation.isPending}
            className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 flex items-center"
          >
            {backtestMutation.isPending ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                実行中...
              </>
            ) : (
              <>
                <PlayCircle className="h-5 w-5 mr-2" />
                バックテスト実行
              </>
            )}
          </button>
        </div>

        {/* Results Section */}
        {backtestResult && (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">最終資金</p>
                    <p className="text-2xl font-bold text-gray-900 mt-2">
                      {formatCurrency(backtestResult.final_budget)}
                    </p>
                  </div>
                  <div className={`p-3 rounded-lg ${
                    backtestResult.profit >= 0 ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'
                  }`}>
                    {backtestResult.profit >= 0 ? <TrendingUp className="h-6 w-6" /> : <TrendingDown className="h-6 w-6" />}
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">利益/損失</p>
                    <p className={`text-2xl font-bold mt-2 ${
                      backtestResult.profit >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {formatCurrency(backtestResult.profit)}
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-yellow-100 text-yellow-600">
                    <DollarSign className="h-6 w-6" />
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">ROI</p>
                    <p className={`text-2xl font-bold mt-2 ${
                      backtestResult.roi >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {formatPercentage(backtestResult.roi / 100)}
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-purple-100 text-purple-600">
                    <TrendingUp className="h-6 w-6" />
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">的中率</p>
                    <p className="text-2xl font-bold text-gray-900 mt-2">
                      {formatPercentage(backtestResult.win_rate / 100)}
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-blue-100 text-blue-600">
                    <Target className="h-6 w-6" />
                  </div>
                </div>
              </div>
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
              {/* Budget Progress Chart */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">資金推移</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="race" label={{ value: 'レース', position: 'insideBottom', offset: -5 }} />
                    <YAxis />
                    <Tooltip formatter={(value) => formatCurrency(Number(value))} />
                    <Legend />
                    <Line type="monotone" dataKey="budget" stroke="#3B82F6" name="資金" strokeWidth={2} />
                    <Line type="monotone" dataKey="profit" stroke="#10B981" name="利益" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Bet Results Chart */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">ベット結果</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="race" label={{ value: 'レース', position: 'insideBottom', offset: -5 }} />
                    <YAxis />
                    <Tooltip formatter={(value) => formatCurrency(Number(value))} />
                    <Legend />
                    <Bar dataKey="bet" fill="#F59E0B" name="ベット額" />
                    <Bar dataKey="win" fill="#10B981" name="払戻金" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Detailed Statistics */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">詳細統計</h3>
              
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-sm text-gray-600">期間</p>
                  <p className="font-semibold">
                    {format(new Date(backtestResult.period.start), 'yyyy/MM/dd')} -
                    {format(new Date(backtestResult.period.end), 'yyyy/MM/dd')}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">総レース数</p>
                  <p className="font-semibold">{backtestResult.num_races}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">総ベット数</p>
                  <p className="font-semibold">{backtestResult.total_bets}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">的中数</p>
                  <p className="font-semibold">{backtestResult.total_wins}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">総投資額</p>
                  <p className="font-semibold">{formatCurrency(backtestResult.total_bet_amount)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">総払戻金</p>
                  <p className="font-semibold">{formatCurrency(backtestResult.total_return)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">平均ベット額</p>
                  <p className="font-semibold">
                    {formatCurrency(backtestResult.total_bet_amount / backtestResult.total_bets)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">平均払戻金</p>
                  <p className="font-semibold">
                    {formatCurrency(backtestResult.total_return / backtestResult.total_wins)}
                  </p>
                </div>
              </div>
            </div>
          </>
        )}

        {/* Error Message */}
        {backtestMutation.isError && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-8">
            <p className="text-red-600">バックテストの実行に失敗しました。設定を確認してください。</p>
          </div>
        )}
      </main>
    </div>
  );
}