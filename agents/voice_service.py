import edge_tts
import asyncio
import os
from typing import Optional, Dict
from pathlib import Path


class VoiceService:
    """
    Free Text-to-Speech service using Microsoft Edge TTS
    - 100% FREE
    - NO API keys needed
    - HIGH QUALITY voices
    - UNLIMITED usage
    - Python 3.13+ compatible
    """
    
    VOICES = {
        'female': 'en-US-AriaNeural',
        'male': 'en-US-GuyNeural',
        'female_uk': 'en-GB-SoniaNeural',
        'male_uk': 'en-GB-RyanNeural',
        'female_au': 'en-AU-NatashaNeural',
    }
    
    def __init__(self, voice: str = 'female'):
        """
        Initialize voice service
        
        Args:
            voice: Voice type - 'female', 'male', 'female_uk', 'male_uk', 'female_au'
        """
        self.voice_name = self.VOICES.get(voice, self.VOICES['female'])
        print(f"🔊 Voice Service initialized with {voice} voice ({self.voice_name})")
    
    async def text_to_speech_async(self, text: str) -> bytes:
        """
        Convert text to speech asynchronously
        
        Args:
            text: Text to convert
            
        Returns:
            Audio bytes in MP3 format
        """
        communicate = edge_tts.Communicate(text, self.voice_name)
        audio_data = b""
        
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        
        return audio_data
    
    def text_to_speech(self, text: str) -> bytes:
        """
        Convert text to speech (synchronous wrapper)
        
        Args:
            text: Text to convert
            
        Returns:
            Audio bytes in MP3 format
        """
        try:
            # Try to get the current event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, we can't use asyncio.run()
                # This will be handled by the async version
                raise RuntimeError("Use text_to_speech_async() in async context")
            return asyncio.run(self.text_to_speech_async(text))
        except RuntimeError:
            # Create a new event loop if needed
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.text_to_speech_async(text))
            finally:
                loop.close()
    
    async def synthesize_to_file_async(self, text: str, output_path: str) -> Dict:
        """
        Synthesize text to speech and save to file (async)
        
        Args:
            text: Text to convert
            output_path: Path to save audio file
            
        Returns:
            Result dictionary with success status
        """
        try:
            print(f"🎵 Synthesizing: {text[:50]}...")
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            
            # Generate speech
            audio_bytes = await self.text_to_speech_async(text)
            
            # Save to file
            with open(output_path, 'wb') as f:
                f.write(audio_bytes)
            
            print(f"Audio saved: {output_path}")
            
            return {
                "success": True,
                "path": output_path,
                "text": text
            }
            
        except Exception as e:
            print(f"TTS error: {e}")
            return {
                "success": False,
                "error": str(e),
                "text": text
            }
    
    def synthesize_to_file(self, text: str, output_path: str) -> Dict:
        """
        Synthesize text to speech and save to file (sync wrapper)
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.synthesize_to_file_async(text, output_path))
        finally:
            loop.close()
    
    async def synthesize_to_bytes_async(self, text: str) -> Dict:
        """
        Synthesize text to speech and return bytes (async)
        
        Args:
            text: Text to convert
            
        Returns:
            Result dictionary with audio bytes
        """
        try:
            print(f"Synthesizing: {text[:50]}...")
            audio_bytes = await self.text_to_speech_async(text)
            
            print(f"Audio generated ({len(audio_bytes)} bytes)")
            
            return {
                "success": True,
                "audio_bytes": audio_bytes,
                "text": text
            }
            
        except Exception as e:
            print(f"TTS error: {e}")
            return {
                "success": False,
                "error": str(e),
                "text": text
            }
    
    def synthesize_to_bytes(self, text: str) -> Dict:
        """
        Synthesize text to speech and return bytes (sync wrapper)
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.synthesize_to_bytes_async(text))
        finally:
            loop.close()


# Global instance for reuse
_voice_service: Optional[VoiceService] = None


def get_voice_service(voice: str = 'female') -> VoiceService:
    """
    Get or create global voice service instance
    
    Args:
        voice: Voice type
        
    Returns:
        VoiceService instance
    """
    global _voice_service
    if _voice_service is None:
        _voice_service = VoiceService(voice=voice)
    return _voice_service

