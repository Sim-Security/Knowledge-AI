"""
System utilities for hardware detection and Ollama management.
Enables smart auto-configuration for local/offline operation.
"""

import platform
import subprocess
import psutil
import asyncio
import httpx
from typing import Dict, List, Optional, Tuple
from pathlib import Path


class HardwareDetector:
    """Detect system hardware capabilities."""

    @staticmethod
    def get_system_info() -> Dict:
        """Get comprehensive system information."""
        return {
            "os": platform.system(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "cpu_count": psutil.cpu_count(logical=True),
            "cpu_physical_cores": psutil.cpu_count(logical=False),
            "total_ram_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "available_ram_gb": round(psutil.virtual_memory().available / (1024**3), 2),
        }

    @staticmethod
    def detect_gpu() -> Dict:
        """Detect GPU information using various methods."""
        gpu_info = {
            "has_gpu": False,
            "gpu_type": None,
            "gpu_count": 0,
            "vram_gb": 0,
            "gpus": []
        }

        # Try NVIDIA first
        nvidia_info = HardwareDetector._detect_nvidia()
        if nvidia_info["has_gpu"]:
            return nvidia_info

        # Try AMD
        amd_info = HardwareDetector._detect_amd()
        if amd_info["has_gpu"]:
            return amd_info

        # Try Apple Silicon
        apple_info = HardwareDetector._detect_apple_silicon()
        if apple_info["has_gpu"]:
            return apple_info

        # Try Intel
        intel_info = HardwareDetector._detect_intel()
        if intel_info["has_gpu"]:
            return intel_info

        return gpu_info

    @staticmethod
    def _detect_nvidia() -> Dict:
        """Detect NVIDIA GPU using nvidia-smi."""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                gpus = []
                total_vram = 0

                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split(',')
                        name = parts[0].strip()
                        vram_mb = int(parts[1].strip().split()[0])
                        vram_gb = round(vram_mb / 1024, 2)

                        gpus.append({
                            "name": name,
                            "vram_gb": vram_gb
                        })
                        total_vram += vram_gb

                return {
                    "has_gpu": True,
                    "gpu_type": "NVIDIA",
                    "gpu_count": len(gpus),
                    "vram_gb": total_vram,
                    "gpus": gpus
                }
        except (subprocess.SubprocessError, FileNotFoundError, IndexError):
            pass

        return {"has_gpu": False}

    @staticmethod
    def _detect_amd() -> Dict:
        """Detect AMD GPU using rocm-smi or lspci."""
        try:
            # Try rocm-smi first
            result = subprocess.run(
                ["rocm-smi", "--showproductname"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0 and "GPU" in result.stdout:
                # Parse AMD GPU info
                return {
                    "has_gpu": True,
                    "gpu_type": "AMD",
                    "gpu_count": 1,
                    "vram_gb": 8,  # Default estimate
                    "gpus": [{"name": "AMD GPU", "vram_gb": 8}]
                }
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        # Try lspci as fallback
        try:
            result = subprocess.run(
                ["lspci"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if "AMD" in result.stdout and "VGA" in result.stdout:
                return {
                    "has_gpu": True,
                    "gpu_type": "AMD",
                    "gpu_count": 1,
                    "vram_gb": 8,  # Default estimate
                    "gpus": [{"name": "AMD GPU", "vram_gb": 8}]
                }
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        return {"has_gpu": False}

    @staticmethod
    def _detect_apple_silicon() -> Dict:
        """Detect Apple Silicon (M1/M2/M3) on macOS."""
        if platform.system() != "Darwin":
            return {"has_gpu": False}

        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
                timeout=5
            )

            cpu_info = result.stdout.strip()

            if "Apple" in cpu_info:
                # Detect M-series chip
                chip_type = "Apple Silicon"
                vram_gb = 8  # Default unified memory

                if "M1" in cpu_info:
                    chip_type = "Apple M1"
                    vram_gb = 16  # Typical M1 unified memory
                elif "M2" in cpu_info:
                    chip_type = "Apple M2"
                    vram_gb = 24  # Typical M2 unified memory
                elif "M3" in cpu_info:
                    chip_type = "Apple M3"
                    vram_gb = 24  # Typical M3 unified memory
                elif "M4" in cpu_info:
                    chip_type = "Apple M4"
                    vram_gb = 32  # Typical M4 unified memory

                return {
                    "has_gpu": True,
                    "gpu_type": "Apple Silicon",
                    "gpu_count": 1,
                    "vram_gb": vram_gb,
                    "gpus": [{"name": chip_type, "vram_gb": vram_gb}]
                }
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        return {"has_gpu": False}

    @staticmethod
    def _detect_intel() -> Dict:
        """Detect Intel integrated graphics."""
        try:
            result = subprocess.run(
                ["lspci"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if "Intel" in result.stdout and ("VGA" in result.stdout or "Display" in result.stdout):
                return {
                    "has_gpu": True,
                    "gpu_type": "Intel Integrated",
                    "gpu_count": 1,
                    "vram_gb": 2,  # Shared memory estimate
                    "gpus": [{"name": "Intel Integrated Graphics", "vram_gb": 2}]
                }
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        return {"has_gpu": False}


class ModelRecommender:
    """Recommend best local models based on hardware."""

    # Model database with hardware requirements
    MODELS = {
        # Chat models
        "chat": {
            "llama3.2:1b": {
                "name": "Llama 3.2 1B",
                "size_gb": 1.3,
                "min_ram_gb": 4,
                "min_vram_gb": 0,
                "speed": "very_fast",
                "quality": "good",
                "description": "Tiny but capable, runs on anything"
            },
            "llama3.2:3b": {
                "name": "Llama 3.2 3B",
                "size_gb": 2.0,
                "min_ram_gb": 6,
                "min_vram_gb": 0,
                "speed": "fast",
                "quality": "very_good",
                "description": "Great balance of speed and quality"
            },
            "phi3:mini": {
                "name": "Phi-3 Mini (3.8B)",
                "size_gb": 2.3,
                "min_ram_gb": 6,
                "min_vram_gb": 0,
                "speed": "fast",
                "quality": "very_good",
                "description": "Microsoft's efficient model"
            },
            "llama3.2": {
                "name": "Llama 3.2 (8B)",
                "size_gb": 4.7,
                "min_ram_gb": 8,
                "min_vram_gb": 4,
                "speed": "medium",
                "quality": "excellent",
                "description": "Best balanced model, great quality"
            },
            "gemma2:9b": {
                "name": "Gemma 2 9B",
                "size_gb": 5.4,
                "min_ram_gb": 10,
                "min_vram_gb": 6,
                "speed": "medium",
                "quality": "excellent",
                "description": "Google's powerful model"
            },
            "mistral": {
                "name": "Mistral 7B",
                "size_gb": 4.1,
                "min_ram_gb": 8,
                "min_vram_gb": 4,
                "speed": "medium",
                "quality": "excellent",
                "description": "Popular open-source model"
            },
            "llama3.1:70b": {
                "name": "Llama 3.1 70B",
                "size_gb": 40,
                "min_ram_gb": 64,
                "min_vram_gb": 40,
                "speed": "slow",
                "quality": "best",
                "description": "Highest quality, needs powerful hardware"
            },
        },
        # Embedding models
        "embedding": {
            "nomic-embed-text": {
                "name": "Nomic Embed Text",
                "size_gb": 0.3,
                "min_ram_gb": 2,
                "min_vram_gb": 0,
                "dimensions": 768,
                "speed": "very_fast",
                "quality": "very_good",
                "description": "Fast and efficient embeddings"
            },
            "mxbai-embed-large": {
                "name": "MixedBread Large",
                "size_gb": 0.7,
                "min_ram_gb": 4,
                "min_vram_gb": 0,
                "dimensions": 1024,
                "speed": "fast",
                "quality": "excellent",
                "description": "High-quality embeddings"
            },
            "all-minilm": {
                "name": "All-MiniLM",
                "size_gb": 0.1,
                "min_ram_gb": 2,
                "min_vram_gb": 0,
                "dimensions": 384,
                "speed": "very_fast",
                "quality": "good",
                "description": "Smallest and fastest"
            },
        }
    }

    @staticmethod
    def recommend_models(hardware: Dict) -> Dict:
        """Recommend best models for given hardware."""
        system_info = hardware.get("system", {})
        gpu_info = hardware.get("gpu", {})

        available_ram = system_info.get("available_ram_gb", 0)
        total_ram = system_info.get("total_ram_gb", 0)
        has_gpu = gpu_info.get("has_gpu", False)
        vram = gpu_info.get("vram_gb", 0)
        gpu_type = gpu_info.get("gpu_type", "")

        # Determine hardware tier
        tier = ModelRecommender._determine_tier(available_ram, has_gpu, vram, gpu_type)

        # Get recommendations for each tier
        chat_rec = ModelRecommender._recommend_chat(available_ram, vram, tier)
        embed_rec = ModelRecommender._recommend_embedding(available_ram, tier)
        
        # Calculate total download size
        chat_size = chat_rec.get("info", {}).get("size_gb", 0)
        embed_size = embed_rec.get("info", {}).get("size_gb", 0)
        total_size = chat_size + embed_size
        
        # Determine provider strategy based on tier
        provider_strategy = ModelRecommender._get_provider_strategy(tier, has_gpu, vram)
        
        recommendations = {
            "tier": tier,
            "tier_description": ModelRecommender._get_tier_description(tier),
            "provider_strategy": provider_strategy,
            "chat": chat_rec,
            "embedding": embed_rec,
            "download_info": {
                "total_size_gb": round(total_size, 1),
                "chat_size_gb": chat_size,
                "embedding_size_gb": embed_size,
                "download_source": "ollama.ai/library (open-source models)",
                "storage_location": "~/.ollama/models/",
                "estimated_download_time": ModelRecommender._estimate_download_time(total_size),
            },
            "hardware_summary": {
                "ram_gb": available_ram,
                "total_ram_gb": total_ram,
                "has_gpu": has_gpu,
                "gpu_type": gpu_type,
                "vram_gb": vram
            },
            "all_models": {
                "chat": ModelRecommender.MODELS["chat"],
                "embedding": ModelRecommender.MODELS["embedding"],
            }
        }

        return recommendations
    
    @staticmethod
    def _get_provider_strategy(tier: str, has_gpu: bool, vram_gb: float) -> Dict:
        """Recommend best provider strategy based on hardware."""
        strategies = {
            "high_end": {
                "recommended": "local",
                "reason": "Your hardware can run high-quality local models with excellent speed",
                "chat_provider": "ollama",
                "embedding_provider": "ollama",
                "expected_speed": "⚡ Fast (10-50 tokens/sec)",
                "privacy": "🔒 Maximum - No data leaves your device",
                "cost": "💰 Free after download",
            },
            "mid_high": {
                "recommended": "local",
                "reason": "Your hardware is well-suited for local models",
                "chat_provider": "ollama",
                "embedding_provider": "ollama", 
                "expected_speed": "⚡ Good (5-20 tokens/sec)",
                "privacy": "🔒 Maximum - No data leaves your device",
                "cost": "💰 Free after download",
            },
            "mid": {
                "recommended": "hybrid",
                "reason": "Use local embeddings for privacy, cloud for complex queries when speed matters",
                "chat_provider": "openrouter",
                "embedding_provider": "ollama",
                "expected_speed": "⚡ Fast embeddings, cloud chat",
                "privacy": "🔐 Partial - Embeddings local, queries go to cloud",
                "cost": "💵 Low cost (OpenRouter pay-per-use)",
                "alternative": {
                    "name": "Full Local (slower)",
                    "chat_provider": "ollama",
                    "embedding_provider": "ollama",
                    "expected_speed": "🐢 Slower (2-10 tokens/sec)",
                }
            },
            "low_mid": {
                "recommended": "hybrid",
                "reason": "Local embeddings work, but cloud chat recommended for responsiveness",
                "chat_provider": "openrouter",
                "embedding_provider": "ollama",
                "expected_speed": "⚡ Fast embeddings, cloud chat",
                "privacy": "🔐 Partial - Embeddings local, queries go to cloud",
                "cost": "💵 Low cost (OpenRouter pay-per-use)",
                "alternative": {
                    "name": "Full Local (slow)",
                    "chat_provider": "ollama",
                    "embedding_provider": "ollama",
                    "expected_speed": "🐢 Slow (1-5 tokens/sec)",
                }
            },
            "low": {
                "recommended": "cloud",
                "reason": "Cloud providers recommended for good performance on your hardware",
                "chat_provider": "openrouter",
                "embedding_provider": "openrouter",
                "expected_speed": "⚡ Fast (cloud-based)",
                "privacy": "🌐 Standard - Data processed by cloud providers",
                "cost": "💵 Pay-per-use (OpenRouter)",
                "alternative": {
                    "name": "Full Local (very slow, testing only)",
                    "chat_provider": "ollama",
                    "embedding_provider": "ollama",
                    "expected_speed": "🐌 Very slow (<1 token/sec)",
                }
            },
        }
        return strategies.get(tier, strategies["low"])
    
    @staticmethod
    def _estimate_download_time(size_gb: float) -> str:
        """Estimate download time based on typical connection speeds."""
        # Assume 50 Mbps average
        seconds = (size_gb * 1024 * 8) / 50
        if seconds < 60:
            return f"~{int(seconds)} seconds"
        elif seconds < 3600:
            return f"~{int(seconds / 60)} minutes"
        else:
            return f"~{int(seconds / 3600)} hours"

    @staticmethod
    def _determine_tier(ram_gb: float, has_gpu: bool, vram_gb: float, gpu_type: str) -> str:
        """Determine hardware tier."""
        # High-end: Powerful GPU with lots of VRAM
        if vram_gb >= 16 and ram_gb >= 32:
            return "high_end"

        # Mid-high: Good GPU or Apple Silicon
        if (vram_gb >= 8 or "Apple Silicon" in gpu_type) and ram_gb >= 16:
            return "mid_high"

        # Mid: Moderate GPU or good CPU
        if (vram_gb >= 4 or has_gpu) and ram_gb >= 8:
            return "mid"

        # Low-mid: Minimal GPU or decent CPU
        if ram_gb >= 6:
            return "low_mid"

        # Low: Limited resources
        return "low"

    @staticmethod
    def _get_tier_description(tier: str) -> str:
        """Get human-readable tier description."""
        descriptions = {
            "high_end": "🚀 High-End - Can run largest models with excellent performance",
            "mid_high": "💪 Mid-High - Can run most models with good performance",
            "mid": "⚡ Mid-Range - Can run medium models with decent performance",
            "low_mid": "📱 Low-Mid - Can run small models efficiently",
            "low": "💡 Basic - Can run tiny models, suitable for testing"
        }
        return descriptions.get(tier, "Unknown tier")

    @staticmethod
    def _recommend_chat(ram_gb: float, vram_gb: float, tier: str) -> Dict:
        """Recommend chat models."""
        models = ModelRecommender.MODELS["chat"]

        # Filter compatible models
        compatible = [
            (key, info) for key, info in models.items()
            if info["min_ram_gb"] <= ram_gb and info["min_vram_gb"] <= vram_gb
        ]

        if not compatible:
            # Fallback to smallest model
            return {
                "recommended": "llama3.2:1b",
                "alternatives": [],
                "info": models["llama3.2:1b"]
            }

        # Sort by quality (best first)
        quality_order = ["best", "excellent", "very_good", "good"]
        compatible.sort(key=lambda x: quality_order.index(x[1]["quality"]) if x[1]["quality"] in quality_order else 999)

        recommended_key, recommended_info = compatible[0]
        alternatives = [key for key, _ in compatible[1:4]]  # Top 3 alternatives

        return {
            "recommended": recommended_key,
            "alternatives": alternatives,
            "info": recommended_info
        }

    @staticmethod
    def _recommend_embedding(ram_gb: float, tier: str) -> Dict:
        """Recommend embedding models."""
        models = ModelRecommender.MODELS["embedding"]

        # Always recommend nomic-embed-text as default (best balance)
        if ram_gb >= 4:
            return {
                "recommended": "mxbai-embed-large",
                "alternatives": ["nomic-embed-text", "all-minilm"],
                "info": models["mxbai-embed-large"]
            }
        else:
            return {
                "recommended": "nomic-embed-text",
                "alternatives": ["all-minilm"],
                "info": models["nomic-embed-text"]
            }


class OllamaManager:
    """Manage Ollama installation and models."""

    @staticmethod
    async def check_ollama_installed() -> Dict:
        """Check if Ollama is installed and running."""
        try:
            # Try to connect to Ollama API
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get("http://localhost:11434/api/version")

                if response.status_code == 200:
                    version_info = response.json()
                    return {
                        "installed": True,
                        "running": True,
                        "version": version_info.get("version", "unknown")
                    }
        except (httpx.ConnectError, httpx.TimeoutException):
            # Ollama not running
            pass

        # Check if ollama command exists
        try:
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                return {
                    "installed": True,
                    "running": False,
                    "version": result.stdout.strip()
                }
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        return {
            "installed": False,
            "running": False,
            "version": None
        }

    @staticmethod
    async def list_models() -> List[Dict]:
        """List installed Ollama models."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:11434/api/tags")

                if response.status_code == 200:
                    data = response.json()
                    return [
                        {
                            "name": model["name"],
                            "size_gb": round(model.get("size", 0) / (1024**3), 2),
                            "modified": model.get("modified_at", "")
                        }
                        for model in data.get("models", [])
                    ]
        except Exception:
            pass

        return []

    @staticmethod
    async def pull_model(model_name: str) -> Dict:
        """Pull an Ollama model (non-blocking)."""
        try:
            # Start pull in background
            process = subprocess.Popen(
                ["ollama", "pull", model_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            return {
                "success": True,
                "message": f"Started pulling {model_name}",
                "model": model_name
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    async def get_pull_status(model_name: str) -> Dict:
        """Check if a model is being pulled or is ready."""
        models = await OllamaManager.list_models()

        for model in models:
            if model_name in model["name"]:
                return {
                    "status": "ready",
                    "model": model_name,
                    "size_gb": model["size_gb"]
                }

        # Check if pull is in progress (simplified check)
        try:
            result = subprocess.run(
                ["pgrep", "-f", f"ollama pull {model_name}"],
                capture_output=True,
                timeout=2
            )

            if result.returncode == 0:
                return {
                    "status": "pulling",
                    "model": model_name
                }
        except Exception:
            pass

        return {
            "status": "not_started",
            "model": model_name
        }
