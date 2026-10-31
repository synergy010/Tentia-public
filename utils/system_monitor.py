#!/usr/bin/env python3
"""
System resource monitor for t2.micro optimization
"""

import psutil
import gc
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SystemMonitor:
    """Monitor system resources for t2.micro optimization"""
    
    def __init__(self):
        self.memory_threshold = 0.8  # 80% memory usage threshold
        self.cpu_threshold = 0.9     # 90% CPU usage threshold
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get current system statistics"""
        try:
            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage = {
                'total_gb': round(memory.total / (1024**3), 2),
                'available_gb': round(memory.available / (1024**3), 2),
                'used_gb': round(memory.used / (1024**3), 2),
                'percent': memory.percent,
                'is_critical': memory.percent > 90
            }
            
            # CPU usage
            cpu_usage = {
                'percent': psutil.cpu_percent(interval=1),
                'count': psutil.cpu_count(),
                'is_critical': psutil.cpu_percent(interval=1) > 90
            }
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage = {
                'total_gb': round(disk.total / (1024**3), 2),
                'used_gb': round(disk.used / (1024**3), 2),
                'free_gb': round(disk.free / (1024**3), 2),
                'percent': round((disk.used / disk.total) * 100, 2)
            }
            
            return {
                'memory': memory_usage,
                'cpu': cpu_usage,
                'disk': disk_usage,
                'timestamp': psutil.boot_time()
            }
            
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {}
    
    def check_memory_pressure(self) -> bool:
        """Check if memory pressure is high"""
        try:
            memory = psutil.virtual_memory()
            return memory.percent > (self.memory_threshold * 100)
        except Exception as e:
            logger.error(f"Error checking memory pressure: {e}")
            return False
    
    def force_cleanup(self):
        """Force garbage collection and memory cleanup"""
        try:
            # Force garbage collection
            collected = gc.collect()
            logger.info(f"Garbage collection freed {collected} objects")
            
            # Clear Python cache if available
            if hasattr(gc, 'clear_cache'):
                gc.clear_cache()
                logger.info("Python cache cleared")
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def get_optimization_recommendations(self) -> list:
        """Get optimization recommendations based on current stats"""
        recommendations = []
        stats = self.get_system_stats()
        
        if not stats:
            return ["Unable to get system stats"]
        
        # Memory recommendations
        memory = stats.get('memory', {})
        if memory.get('percent', 0) > 80:
            recommendations.append("High memory usage - consider reducing worker pool size")
        if memory.get('percent', 0) > 90:
            recommendations.append("Critical memory usage - force cleanup recommended")
        
        # CPU recommendations
        cpu = stats.get('cpu', {})
        if cpu.get('percent', 0) > 80:
            recommendations.append("High CPU usage - consider reducing concurrent users")
        if cpu.get('percent', 0) > 90:
            recommendations.append("Critical CPU usage - system may be overloaded")
        
        # General recommendations for t2.micro
        recommendations.extend([
            "t2.micro has limited resources - monitor closely",
            "Use memory-efficient methods for large datasets",
            "Consider chunked processing for heavy operations"
        ])
        
        return recommendations
    
    def log_system_health(self):
        """Log current system health status"""
        stats = self.get_system_stats()
        if not stats:
            logger.warning("Unable to get system stats")
            return
        
        memory = stats.get('memory', {})
        cpu = stats.get('cpu', {})
        
        logger.info(f"System Health - Memory: {memory.get('percent', 0)}%, CPU: {cpu.get('percent', 0)}%")
        
        if memory.get('is_critical', False):
            logger.critical(f"CRITICAL: Memory usage at {memory.get('percent', 0)}%")
            self.force_cleanup()
        
        if cpu.get('is_critical', False):
            logger.critical(f"CRITICAL: CPU usage at {cpu.get('percent', 0)}%")

# Global instance
system_monitor = SystemMonitor()
