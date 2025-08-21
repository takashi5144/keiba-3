/**
 * Type definitions for the application
 */

// Race types
export interface Race {
  id: string;
  date: string;
  place: string;
  race_number: number;
  race_name?: string;
  distance: number;
  track_type: string;
  weather?: string;
  track_condition?: string;
  grade?: string;
  prize_money?: number;
}

export interface RaceResult {
  id: string;
  race_id: string;
  post_position: number;
  bracket_number: number;
  horse_name: string;
  horse_id: string;
  sex: string;
  age: number;
  jockey_name: string;
  trainer_name: string;
  weight: number;
  horse_weight?: number;
  weight_diff?: number;
  finish_position?: number;
  time?: string;
  odds?: number;
  popularity?: number;
}

// Prediction types
export interface HorsePrediction {
  post_position: number;
  horse_name: string;
  horse_id: string;
  jockey_name: string;
  win_probability: number;
  predicted_rank: number;
  odds?: number;
  expected_value?: number;
  recommended_bet?: boolean;
}

export interface BettingRecommendation {
  post_position: number;
  horse_name: string;
  bet_amount: number;
  expected_value: number;
  win_probability: number;
  odds: number;
}

export interface BettingStrategy {
  recommended_bets: BettingRecommendation[];
  total_bet_amount: number;
  expected_return: number;
  expected_profit: number;
  roi: number;
  strategy: string;
  confidence: string;
  reason?: string;
}

export interface RacePrediction {
  race_id: string;
  race_date: string;
  place: string;
  race_number: number;
  race_name?: string;
  num_horses: number;
  predictions: HorsePrediction[];
  betting_strategy: BettingStrategy;
}

// Training types
export interface TrainingMetrics {
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  roc_auc: number;
  log_loss: number;
  race_accuracy?: number;
  total_races_evaluated?: number;
  roi?: number;
  num_bets?: number;
  num_wins?: number;
  win_rate?: number;
}

export interface TrainingResult {
  model_type: string;
  best_params: Record<string, any>;
  train_metrics: TrainingMetrics;
  test_metrics: TrainingMetrics;
  feature_importance?: Record<string, number>;
  train_samples: number;
  test_samples: number;
  train_races: number;
  test_races: number;
  trained_at: string;
  model_path?: string;
}

// Backtest types
export interface BacktestResult {
  period: {
    start: string;
    end: string;
  };
  initial_budget: number;
  final_budget: number;
  profit: number;
  roi: number;
  total_bets: number;
  total_wins: number;
  win_rate: number;
  total_bet_amount: number;
  total_return: number;
  num_races: number;
  results_sample: Array<{
    race_id: string;
    bet_amount: number;
    win: boolean;
    odds: number;
    expected_value: number;
    budget_after: number;
  }>;
}

// Model types
export interface Model {
  filename: string;
  path: string;
  model_name: string;
  trained_at?: string;
  metrics: TrainingMetrics;
  version: string;
}

// Task types
export interface TaskStatus {
  state: 'PENDING' | 'PROGRESS' | 'SUCCESS' | 'FAILURE';
  current?: number;
  total?: number;
  status?: string;
  result?: any;
  error?: string;
}