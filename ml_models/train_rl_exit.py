"""
Train PPO (Proximal Policy Optimization) agent for optimal exit timing.

This script trains an RL agent using stable-baselines3 to learn when to exit
trading positions for maximum profit.
"""
import os
import sys
sys.path.insert(0, os.getcwd())

import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor
from ml_models.rl_exit_env import NBAExitEnv
from ml_models.rl_data_split import load_split


def make_env(game_files, rank=0):
    """
    Create a single environment instance.
    
    Args:
        game_files: List of game file paths
        rank: Unique ID for this environment
    """
    def _init():
        env = NBAExitEnv(
            game_files=game_files,
            entry_threshold=0.60,
            contracts=500,
            max_hold_minutes=30
        )
        env = Monitor(env)  # Wrap for logging
        return env
    return _init


def train_ppo(
    train_games,
    val_games,
    total_timesteps=500_000,
    save_freq=25_000,
    eval_freq=10_000,
    output_dir='ml_models/outputs'
):
    """
    Train PPO agent on exit timing task.
    
    Args:
        train_games: List of training game files
        val_games: List of validation game files
        total_timesteps: Total training steps
        save_freq: Save checkpoint every N steps
        eval_freq: Evaluate on validation set every N steps
        output_dir: Directory to save models and logs
    """
    print("="*80)
    print("TRAINING PPO AGENT FOR EXIT TIMING")
    print("="*80)
    
    print(f"\nTraining games: {len(train_games)}")
    print(f"Validation games: {len(val_games)}")
    print(f"Total timesteps: {total_timesteps:,}")
    
    # Create training environment
    print("\nCreating training environment...")
    train_env = DummyVecEnv([make_env(train_games, i) for i in range(1)])
    
    # Create evaluation environment
    print("Creating evaluation environment...")
    eval_env = DummyVecEnv([make_env(val_games, i) for i in range(1)])
    
    # Create callbacks
    checkpoint_dir = os.path.join(output_dir, 'rl_checkpoints')
    log_dir = os.path.join(output_dir, 'rl_logs')
    os.makedirs(checkpoint_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    
    checkpoint_callback = CheckpointCallback(
        save_freq=save_freq,
        save_path=checkpoint_dir,
        name_prefix='rl_exit_model'
    )
    
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=output_dir,
        log_path=log_dir,
        eval_freq=eval_freq,
        deterministic=True,
        render=False,
        n_eval_episodes=10,
        verbose=1
    )
    
    # Initialize PPO model
    print("\nInitializing PPO agent...")
    print("Hyperparameters:")
    print("  Learning rate: 3e-4")
    print("  Batch size: 64")
    print("  N steps: 2048")
    print("  N epochs: 10")
    print("  Gamma: 0.99")
    print("  GAE lambda: 0.95")
    print("  Clip range: 0.2")
    print("  Entropy coefficient: 0.01")
    
    model = PPO(
        "MlpPolicy",
        train_env,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,
        vf_coef=0.5,
        max_grad_norm=0.5,
        verbose=1,
        tensorboard_log=log_dir
    )
    
    # Train
    print("\n" + "="*80)
    print("STARTING TRAINING")
    print("="*80)
    print("\nThis may take 1-3 hours depending on your hardware...")
    print("Press Ctrl+C to stop training early (model will be saved)")
    print("\nMonitor training with TensorBoard:")
    print(f"  tensorboard --logdir {log_dir}\n")
    
    try:
        model.learn(
            total_timesteps=total_timesteps,
            callback=[checkpoint_callback, eval_callback],
            progress_bar=True
        )
    except KeyboardInterrupt:
        print("\n\nTraining interrupted by user!")
    
    # Save final model
    final_model_path = os.path.join(output_dir, 'rl_exit_policy')
    model.save(final_model_path)
    print(f"\n[OK] Final model saved to {final_model_path}")
    
    # Save best model info
    best_model_path = os.path.join(output_dir, 'best_model')
    if os.path.exists(best_model_path + '.zip'):
        print(f"[OK] Best model saved to {best_model_path}")
    
    print("\n" + "="*80)
    print("TRAINING COMPLETE")
    print("="*80)
    
    # Test the trained model
    print("\nTesting trained model on a few validation episodes...")
    test_model(model, val_games[:5])
    
    return model


def test_model(model, test_games, n_episodes=5):
    """
    Test the trained model on a few episodes.
    
    Args:
        model: Trained PPO model
        test_games: List of game files to test on
        n_episodes: Number of episodes to test
    """
    print(f"\nRunning {n_episodes} test episodes...")
    
    env = NBAExitEnv(
        game_files=test_games,
        entry_threshold=0.60,
        contracts=500,
        max_hold_minutes=30
    )
    
    episode_rewards = []
    episode_stats = []
    
    for i in range(n_episodes):
        obs = env.reset()
        done = False
        episode_reward = 0
        
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, done, info = env.step(action)
            episode_reward += reward
        
        stats = env.get_episode_stats()
        episode_rewards.append(episode_reward)
        episode_stats.append(stats)
        
        print(f"  Episode {i+1}: Reward={episode_reward:+.2f}, "
              f"Trades={stats['total_trades']}, "
              f"P/L=${stats['total_pl']:+.2f}, "
              f"Win Rate={stats['win_rate']:.1%}")
    
    print(f"\nAverage episode reward: {np.mean(episode_rewards):+.2f}")
    print(f"Average trades per episode: {np.mean([s['total_trades'] for s in episode_stats]):.1f}")
    print(f"Average P/L per episode: ${np.mean([s['total_pl'] for s in episode_stats]):+.2f}")
    print(f"Average win rate: {np.mean([s['win_rate'] for s in episode_stats]):.1%}")


if __name__ == "__main__":
    # Load data splits
    print("Loading data splits...")
    train_games = load_split('train')
    val_games = load_split('val')
    
    print(f"Training set: {len(train_games)} games")
    print(f"Validation set: {len(val_games)} games")
    
    # Train model
    model = train_ppo(
        train_games=train_games,
        val_games=val_games,
        total_timesteps=500_000,
        save_freq=25_000,
        eval_freq=10_000
    )
    
    print("\n" + "="*80)
    print("Next steps:")
    print("  1. Review training logs in ml_models/outputs/rl_logs/")
    print("  2. Compare RL vs static exit: python ml_models/compare_rl_vs_static.py")
    print("  3. Visualize results: python ml_models/visualize_rl_results.py")
    print("="*80)

