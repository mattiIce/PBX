"""
Call Quality Prediction
Proactive network issue detection using ML
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from pbx.utils.logger import get_logger


class QualityLevel(Enum):
    """Call quality level enumeration"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


class NetworkMetrics:
    """Network metrics for a call or endpoint"""
    
    def __init__(self):
        """Initialize network metrics"""
        self.timestamp = datetime.now()
        self.latency = 0  # milliseconds
        self.jitter = 0   # milliseconds
        self.packet_loss = 0.0  # percentage
        self.bandwidth = 0  # kbps
        self.mos_score = 4.4  # Mean Opinion Score (1.0-5.0)
        
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'latency': self.latency,
            'jitter': self.jitter,
            'packet_loss': self.packet_loss,
            'bandwidth': self.bandwidth,
            'mos_score': self.mos_score
        }


class CallQualityPrediction:
    """
    Call Quality Prediction System
    
    Proactive network issue detection using machine learning.
    Features:
    - Real-time quality prediction
    - Network issue detection before call degradation
    - Historical trend analysis
    - Proactive alerting
    - Recommendation engine
    """
    
    def __init__(self, config=None, db_backend=None):
        """Initialize call quality prediction system"""
        self.logger = get_logger()
        self.config = config or {}
        self.db_backend = db_backend
        self.db = None
        
        # Configuration
        prediction_config = self.config.get('features', {}).get('quality_prediction', {})
        self.enabled = prediction_config.get('enabled', False)
        self.prediction_interval = prediction_config.get('prediction_interval', 5)  # seconds
        self.alert_threshold_mos = prediction_config.get('alert_threshold_mos', 3.5)
        self.alert_threshold_packet_loss = prediction_config.get('alert_threshold_packet_loss', 5.0)
        
        # Historical metrics storage
        self.metrics_history: Dict[str, List[NetworkMetrics]] = {}
        self.max_history_per_endpoint = 1000
        
        # Predictions
        self.active_predictions: Dict[str, Dict] = {}
        
        # Statistics
        self.total_predictions = 0
        self.accurate_predictions = 0
        self.false_positives = 0
        self.alerts_generated = 0
        
        # Initialize database if available
        if self.db_backend and self.db_backend.enabled:
            try:
                from pbx.features.call_quality_prediction_db import CallQualityPredictionDatabase
                self.db = CallQualityPredictionDatabase(self.db_backend)
                self.db.create_tables()
                self.logger.info("Call quality prediction database layer initialized")
            except Exception as e:
                self.logger.warning(f"Could not initialize database layer: {e}")
        
        self.logger.info("Call quality prediction system initialized")
        self.logger.info(f"  Prediction interval: {self.prediction_interval}s")
        self.logger.info(f"  MOS alert threshold: {self.alert_threshold_mos}")
        self.logger.info(f"  Enabled: {self.enabled}")
    
    def collect_metrics(self, call_id: str, metrics: NetworkMetrics):
        """
        Collect network metrics for a call
        
        Args:
            call_id: Call identifier
            metrics: Network metrics
        """
        if call_id not in self.metrics_history:
            self.metrics_history[call_id] = []
        
        self.metrics_history[call_id].append(metrics)
        
        # Limit history size
        if len(self.metrics_history[call_id]) > self.max_history_per_endpoint:
            self.metrics_history[call_id].pop(0)
        
        # Save to database
        if self.db:
            self.db.save_metrics(call_id, metrics.to_dict())
        
        # Trigger prediction
        if self.enabled:
            self._predict_quality(call_id)
    
    def _predict_quality(self, call_id: str) -> Dict:
        """
        Predict future call quality based on current trends
        
        Args:
            call_id: Call identifier
            
        Returns:
            Dict: Prediction result
        """
        if call_id not in self.metrics_history or len(self.metrics_history[call_id]) < 3:
            return {'success': False, 'reason': 'Insufficient data'}
        
        metrics = self.metrics_history[call_id]
        recent = metrics[-10:]  # Last 10 samples
        
        # Calculate trends
        latency_trend = self._calculate_trend([m.latency for m in recent])
        jitter_trend = self._calculate_trend([m.jitter for m in recent])
        packet_loss_trend = self._calculate_trend([m.packet_loss for m in recent])
        mos_trend = self._calculate_trend([m.mos_score for m in recent])
        
        # Predict future MOS score
        # TODO: Replace with ML model (scikit-learn, TensorFlow, etc.)
        current_mos = recent[-1].mos_score
        predicted_mos = current_mos + (mos_trend * 3)  # 3 intervals ahead
        
        # Predict future packet loss
        current_packet_loss = recent[-1].packet_loss
        predicted_packet_loss = current_packet_loss + (packet_loss_trend * 3)
        
        # Determine predicted quality level
        predicted_level = self._quality_level_from_mos(predicted_mos)
        
        # Check for alerts
        alert = False
        alert_reasons = []
        
        if predicted_mos < self.alert_threshold_mos:
            alert = True
            alert_reasons.append(f"MOS predicted to drop to {predicted_mos:.2f}")
        
        if predicted_packet_loss > self.alert_threshold_packet_loss:
            alert = True
            alert_reasons.append(f"Packet loss predicted to reach {predicted_packet_loss:.1f}%")
        
        if latency_trend > 10:  # Increasing latency
            alert_reasons.append("Latency trending upward")
        
        prediction = {
            'call_id': call_id,
            'current_mos': current_mos,
            'predicted_mos': predicted_mos,
            'predicted_quality_level': predicted_level.value,
            'current_packet_loss': current_packet_loss,
            'predicted_packet_loss': predicted_packet_loss,
            'trends': {
                'latency': latency_trend,
                'jitter': jitter_trend,
                'packet_loss': packet_loss_trend,
                'mos': mos_trend
            },
            'alert': alert,
            'alert_reasons': alert_reasons,
            'recommendations': self._generate_recommendations(predicted_mos, predicted_packet_loss),
            'timestamp': datetime.now().isoformat()
        }
        
        self.active_predictions[call_id] = prediction
        self.total_predictions += 1
        
        # Save to database
        if self.db:
            self.db.save_prediction(call_id, prediction)
        
        if alert:
            self.alerts_generated += 1
            self.logger.warning(f"Quality alert for call {call_id}")
            for reason in alert_reasons:
                self.logger.warning(f"  {reason}")
            
            # Save alerts to database
            if self.db:
                for reason in alert_reasons:
                    severity = 'critical' if predicted_mos < 3.0 else 'warning'
                    metric_val = predicted_mos if 'MOS' in reason else predicted_packet_loss
                    thresh_val = self.alert_threshold_mos if 'MOS' in reason else self.alert_threshold_packet_loss
                    self.db.save_alert(call_id, 'quality_degradation', severity, reason, metric_val, thresh_val)
        
        return prediction
    
    def _calculate_trend(self, values: List[float]) -> float:
        """
        Calculate trend direction and magnitude
        
        Args:
            values: List of metric values
            
        Returns:
            float: Trend value (positive = increasing, negative = decreasing)
        """
        if len(values) < 2:
            return 0.0
        
        # Simple linear trend calculation
        # TODO: Use more sophisticated time series analysis
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        
        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def _quality_level_from_mos(self, mos: float) -> QualityLevel:
        """Convert MOS score to quality level"""
        if mos >= 4.3:
            return QualityLevel.EXCELLENT
        elif mos >= 4.0:
            return QualityLevel.GOOD
        elif mos >= 3.6:
            return QualityLevel.FAIR
        elif mos >= 3.1:
            return QualityLevel.POOR
        else:
            return QualityLevel.CRITICAL
    
    def _generate_recommendations(self, predicted_mos: float, 
                                 predicted_packet_loss: float) -> List[str]:
        """
        Generate recommendations based on predictions
        
        Args:
            predicted_mos: Predicted MOS score
            predicted_packet_loss: Predicted packet loss percentage
            
        Returns:
            List[str]: Recommendations
        """
        recommendations = []
        
        if predicted_mos < 3.5:
            recommendations.append("Consider switching to lower bitrate codec")
            recommendations.append("Check network congestion")
        
        if predicted_packet_loss > 5.0:
            recommendations.append("Enable Forward Error Correction (FEC)")
            recommendations.append("Investigate network routing")
        
        if predicted_mos < 3.0:
            recommendations.append("Consider call transfer to alternate route")
            recommendations.append("Alert user of potential quality issues")
        
        return recommendations
    
    def get_prediction(self, call_id: str) -> Optional[Dict]:
        """Get current prediction for a call"""
        return self.active_predictions.get(call_id)
    
    def clear_history(self, call_id: str):
        """Clear metrics history for a call"""
        if call_id in self.metrics_history:
            del self.metrics_history[call_id]
        if call_id in self.active_predictions:
            del self.active_predictions[call_id]
    
    def train_model(self, historical_data: List[Dict]):
        """
        Train ML model with historical data
        
        Args:
            historical_data: List of historical call quality data
        """
        # TODO: Implement ML model training
        # This would use scikit-learn, TensorFlow, or PyTorch
        # Features: latency, jitter, packet_loss, bandwidth, codec, time_of_day
        # Target: future MOS score
        
        self.logger.info(f"Training model with {len(historical_data)} samples")
        # Placeholder for actual training
    
    def get_statistics(self) -> Dict:
        """Get prediction statistics"""
        accuracy = self.accurate_predictions / max(1, self.total_predictions)
        
        stats = {
            'total_predictions': self.total_predictions,
            'accurate_predictions': self.accurate_predictions,
            'false_positives': self.false_positives,
            'prediction_accuracy': accuracy,
            'alerts_generated': self.alerts_generated,
            'active_predictions': len(self.active_predictions),
            'endpoints_monitored': len(self.metrics_history),
            'enabled': self.enabled
        }
        
        # Add database statistics if available
        if self.db:
            db_stats = self.db.get_statistics()
            if db_stats:
                stats['database_stats'] = db_stats
        
        return stats


# Global instance
_quality_prediction = None


def get_quality_prediction(config=None, db_backend=None) -> CallQualityPrediction:
    """Get or create call quality prediction instance"""
    global _quality_prediction
    if _quality_prediction is None:
        _quality_prediction = CallQualityPrediction(config, db_backend)
    return _quality_prediction
