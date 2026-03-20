"""
Simple reward model implementation for RLHF.
"""

import joblib
from typing import Dict, Any, List, Tuple
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
import structlog

from .base import BaseRewardModel, HumanFeedback, FeedbackType

logger = structlog.get_logger()


class SimpleRewardModel(BaseRewardModel):
    """Simple reward model using scikit-learn"""

    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.vectorizer = TfidfVectorizer(max_features=1000)
        self.is_trained = False

    def _extract_features(self, state: Dict[str, Any], action: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Extract text features from state, action, and context"""
        features = []
        
        # Extract text from state
        if "user_request" in state:
            features.append(state["user_request"])
        
        # Extract text from action
        if "agent_name" in action:
            features.append(action["agent_name"])
        if "result" in action:
            features.append(str(action["result"]))
        
        # Extract text from context
        if "workflow_id" in context:
            features.append(context["workflow_id"])
        
        return " ".join(features)

    async def predict_reward(
        self, 
        state: Dict[str, Any], 
        action: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> float:
        """Predict reward for a state-action pair"""
        if not self.is_trained:
            logger.warning("Reward model not trained, returning default reward")
            return 0.5
        
        try:
            feature_text = self._extract_features(state, action, context)
            features = self.vectorizer.transform([feature_text])
            reward = self.model.predict(features)[0]
            
            # Clip reward to reasonable range
            return np.clip(reward, 0.0, 1.0)
        
        except Exception as e:
            logger.error("Error predicting reward", error=str(e))
            return 0.5

    async def train(self, training_data: List[Tuple[Dict[str, Any], float]]):
        """Train the reward model on feedback data"""
        if not training_data:
            logger.warning("No training data provided")
            return

        try:
            # Extract features and targets
            feature_texts = []
            targets = []
            
            for data_point, reward in training_data:
                state = data_point.get("state", {})
                action = data_point.get("action", {})
                context = data_point.get("context", {})
                
                feature_text = self._extract_features(state, action, context)
                feature_texts.append(feature_text)
                targets.append(reward)
            
            # Vectorize features
            X = self.vectorizer.fit_transform(feature_texts)
            y = np.array(targets)
            
            # Train model
            self.model.fit(X, y)
            self.is_trained = True
            
            logger.info("Reward model trained successfully", 
                       training_samples=len(training_data))
        
        except Exception as e:
            logger.error("Error training reward model", error=str(e))
            raise

    async def save(self, path: str):
        """Save the reward model using joblib (safe for sklearn objects)"""
        try:
            model_data = {
                "model": self.model,
                "vectorizer": self.vectorizer,
                "is_trained": self.is_trained,
            }
            joblib.dump(model_data, path)
            logger.info("Reward model saved", path=path)
        except Exception as e:
            logger.error("Error saving reward model", error=str(e))
            raise

    async def load(self, path: str):
        """Load the reward model using joblib"""
        try:
            model_data = joblib.load(path)
            self.model = model_data["model"]
            self.vectorizer = model_data["vectorizer"]
            self.is_trained = model_data["is_trained"]
            logger.info("Reward model loaded", path=path)
        except Exception as e:
            logger.error("Error loading reward model", error=str(e))
            raise


def convert_feedback_to_training_data(feedback_list: List[HumanFeedback]) -> List[Tuple[Dict[str, Any], float]]:
    """Convert human feedback to training data for reward model"""
    training_data = []
    
    for feedback in feedback_list:
        # Convert feedback to reward signal
        if feedback.feedback_type == FeedbackType.THUMBS_UP:
            reward = 1.0
        elif feedback.feedback_type == FeedbackType.THUMBS_DOWN:
            reward = 0.0
        elif feedback.feedback_type == FeedbackType.RATING and feedback.rating:
            reward = feedback.rating / 5.0  # Normalize to 0-1
        else:
            continue  # Skip if no clear reward signal
        
        # Create data point
        data_point = {
            "state": {"user_request": f"workflow_{feedback.workflow_id}"},
            "action": {"run_id": feedback.run_id},
            "context": {"workflow_id": feedback.workflow_id}
        }
        
        training_data.append((data_point, reward))
    
    return training_data
