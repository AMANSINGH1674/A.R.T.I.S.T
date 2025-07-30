"""
Base classes for RLHF (Reinforcement Learning from Human Feedback) system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import structlog

logger = structlog.get_logger()


class FeedbackType(str, Enum):
    """Types of feedback that can be collected"""
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    RATING = "rating"  # 1-5 scale
    DETAILED = "detailed"  # Text feedback
    COMPARISON = "comparison"  # Comparing two outputs


@dataclass
class TrainingExample:
    """Training example for supervised fine-tuning"""
    input_text: str
    target_actions: List[Dict[str, Any]]
    context: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass
class HumanFeedback:
    """Human feedback for reward model training"""
    workflow_id: str
    run_id: str
    user_id: str
    feedback_type: FeedbackType
    rating: Optional[int] = None  # 1-5 scale
    text_feedback: Optional[str] = None
    comparison_preference: Optional[str] = None  # For A/B comparisons
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class RewardSignal:
    """Reward signal for training"""
    workflow_id: str
    run_id: str
    step: str
    reward: float
    source: str  # "human", "automatic", "mixed"
    confidence: float
    metadata: Dict[str, Any] = None


class BaseRewardModel(ABC):
    """Abstract base class for reward models"""
    
    @abstractmethod
    async def predict_reward(
        self, 
        state: Dict[str, Any], 
        action: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> float:
        """Predict reward for a state-action pair"""
        pass
    
    @abstractmethod
    async def train(self, training_data: List[Tuple[Dict[str, Any], float]]):
        """Train the reward model on feedback data"""
        pass
    
    @abstractmethod
    async def save(self, path: str):
        """Save the reward model"""
        pass
    
    @abstractmethod
    async def load(self, path: str):
        """Load the reward model"""
        pass


class BasePolicyOptimizer(ABC):
    """Abstract base class for policy optimization"""
    
    @abstractmethod
    async def optimize_policy(
        self,
        agent_name: str,
        training_episodes: List[Dict[str, Any]],
        reward_model: BaseRewardModel
    ) -> Dict[str, Any]:
        """Optimize agent policy using PPO or similar algorithm"""
        pass


class BaseTrainer(ABC):
    """Abstract base class for training orchestration"""
    
    @abstractmethod
    async def supervised_fine_tune(
        self,
        agent_name: str,
        training_examples: List[TrainingExample]
    ) -> Dict[str, Any]:
        """Perform supervised fine-tuning"""
        pass
    
    @abstractmethod
    async def train_reward_model(
        self,
        feedback_data: List[HumanFeedback]
    ) -> BaseRewardModel:
        """Train reward model from human feedback"""
        pass
    
    @abstractmethod
    async def optimize_policy(
        self,
        agent_name: str,
        reward_model: BaseRewardModel
    ) -> Dict[str, Any]:
        """Optimize agent policy using reinforcement learning"""
        pass
