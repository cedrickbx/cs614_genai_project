import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Heart, Send, Home, Search, PlusSquare, User, Sparkles, Pill, Mic, Volume2, Square } from 'lucide-react';

// API configuration
const API_BASE_URL = '/api';

export default function FoodDrugChatbot() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isListening, setIsListening] = useState(false);
  const [recognition, setRecognition] = useState(null);
  const messagesEndRef = useRef(null);
  const audioRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize Speech Recognition
  useEffect(() => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      const recognitionInstance = new SpeechRecognition();
      
      recognitionInstance.continuous = false;
      recognitionInstance.interimResults = false;
      recognitionInstance.lang = 'en-US';
      
      recognitionInstance.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setInput(transcript);
        setIsListening(false);
      };
      
      recognitionInstance.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsListening(false);
        alert(`Voice recognition error: ${event.error}`);
      };
      
      recognitionInstance.onend = () => {
        setIsListening(false);
      };
      
      setRecognition(recognitionInstance);
    }
  }, []);

  const suggestions = [
    { icon: "🍔", text: "I ate burger at 1pm today" },
    { icon: "🥗", text: "What foods interact with warfarin?" },
    { icon: "💊", text: "Can I take paracetamol with coffee?" },
    { icon: "🍇", text: "Grapefruit and medication interactions" }
  ];

  const handleSubmit = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setError(null);

    try {
      const response = await axios.post(`${API_BASE_URL}/chat`, {
        message: userMessage.content,
        thread_id: 'USER:local'
      });

      const assistantMessage = {
        role: 'assistant',
        content: response.data.message,
        timestamp: response.data.timestamp
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err) {
      console.error('Error sending message:', err);
      setError(err.response?.data?.detail || 'Failed to get response from server');
      
      // Add error message to chat
      const errorMessage = {
        role: 'assistant',
        content: `⚠️ Sorry, I encountered an error: ${err.response?.data?.detail || 'Connection failed'}. Please try again.`,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSuggestionClick = (text) => {
    setInput(text);
  };

  // Voice Recognition
  const startListening = () => {
    if (recognition) {
      setIsListening(true);
      recognition.start();
    } else {
      alert('Speech recognition is not supported in your browser. Please use Chrome, Edge, or Safari.');
    }
  };

  const stopListening = () => {
    if (recognition) {
      recognition.stop();
      setIsListening(false);
    }
  };

  // Text to Speech
  const playAudio = (audioBlob) => {
    const audioUrl = URL.createObjectURL(audioBlob);
    if (audioRef.current) {
      audioRef.current.src = audioUrl;
      audioRef.current.play().catch(err => {
        console.error('Error playing audio:', err);
      });
    }
  };

  const handleSpeakResponse = async (text) => {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/tts`,
        { text, voice: 'female' },
        { responseType: 'blob' }
      );
      playAudio(response.data);
    } catch (err) {
      console.error('Error generating speech:', err);
      alert('Failed to generate speech. Please try again.');
    }
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="h-screen bg-white flex flex-col">
      {/* Instagram Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-3">
        <div className="max-w-2xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-yellow-400 via-pink-500 to-purple-600 p-0.5">
              <div className="w-full h-full rounded-full bg-white flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-purple-600" />
              </div>
            </div>
            <div>
              <div className="font-semibold text-base text-gray-900">Food & Drug AI Assistant</div>
              <div className="text-xs text-gray-500 flex items-center gap-1">
                <span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span>
                Always active • LangGraph powered
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto bg-gradient-to-b from-white to-gray-50">
        <div className="max-w-2xl mx-auto px-4 py-6">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center min-h-[60vh] text-center space-y-6">
              <div className="w-24 h-24 rounded-full bg-gradient-to-tr from-yellow-400 via-pink-500 to-purple-600 p-1">
                <div className="w-full h-full rounded-full bg-white flex items-center justify-center">
                  <Sparkles className="w-12 h-12 text-purple-600" />
                </div>
              </div>
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">
                  Food & Drug Interaction AI
                </h2>
                <p className="text-gray-600 text-sm">
                  Get instant answers about food, medications, and health queries
                </p>
              </div>
              <div className="w-full max-w-md space-y-3 pt-4">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Try asking</p>
                {suggestions.map((suggestion, index) => (
                  <button
                    key={index}
                    onClick={() => handleSuggestionClick(suggestion.text)}
                    className="w-full flex items-center gap-3 p-4 bg-white border border-gray-200 rounded-2xl hover:bg-gray-50 transition-all hover:shadow-md text-left"
                  >
                    <span className="text-2xl">{suggestion.icon}</span>
                    <span className="text-sm text-gray-900">{suggestion.text}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-4 py-4">
              {messages.map((message, index) => (
                <div key={index}>
                  {message.role === 'assistant' ? (
                    <div className="flex gap-3 items-start">
                      <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-yellow-400 via-pink-500 to-purple-600 p-0.5 flex-shrink-0">
                        <div className="w-full h-full rounded-full bg-white flex items-center justify-center">
                          <Sparkles className="w-4 h-4 text-purple-600" />
                        </div>
                      </div>
                      <div className="flex-1 max-w-[85%]">
                        <div className="bg-white border border-gray-200 rounded-3xl rounded-tl-sm px-5 py-3.5 shadow-sm">
                          <p className="text-[15px] text-gray-900 whitespace-pre-wrap leading-relaxed">{message.content}</p>
                        </div>
                        <div className="flex items-center gap-4 px-3 mt-1.5">
                          <span className="text-xs text-gray-400">{formatTimestamp(message.timestamp)}</span>
                          <button
                            onClick={() => handleSpeakResponse(message.content)}
                            className="text-xs text-blue-500 hover:text-blue-600 flex items-center gap-1"
                            title="Listen to response"
                          >
                            <Volume2 className="w-3 h-3" />
                            <span>Listen</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="flex justify-end">
                      <div className="max-w-[85%]">
                        <div className="bg-gradient-to-r from-blue-500 to-blue-600 rounded-3xl rounded-tr-sm px-5 py-3.5 shadow-sm">
                          <p className="text-[15px] text-white whitespace-pre-wrap leading-relaxed">{message.content}</p>
                        </div>
                        <div className="flex items-center justify-end px-3 mt-1.5">
                          <span className="text-xs text-gray-400">{formatTimestamp(message.timestamp)}</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
              
              {isLoading && (
                <div className="flex gap-3 items-start">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-yellow-400 via-pink-500 to-purple-600 p-0.5 flex-shrink-0">
                    <div className="w-full h-full rounded-full bg-white flex items-center justify-center">
                      <Sparkles className="w-4 h-4 text-purple-600" />
                    </div>
                  </div>
                  <div className="bg-white border border-gray-200 rounded-3xl rounded-tl-sm px-5 py-4 shadow-sm">
                    <div className="flex gap-1.5">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </div>

      {/* Warning Banner */}
      <div className="bg-amber-50 border-t border-amber-200 px-4 py-2.5">
        <div className="max-w-2xl mx-auto">
          <p className="text-xs text-amber-800 text-center">
            ⚠️ This AI provides educational information only. Always consult your healthcare provider for medical advice.
          </p>
        </div>
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-gray-200 px-4 py-3">
        <div className="max-w-2xl mx-auto flex items-center gap-3">
          <div className="flex-1 flex items-center gap-3 bg-gray-100 rounded-full px-5 py-2.5 border border-gray-300">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={isListening ? "Listening..." : "Ask about food, medications, or health..."}
              className="flex-1 bg-transparent outline-none text-sm text-gray-900 placeholder-gray-500"
              disabled={isLoading || isListening}
            />
          </div>
          {isListening ? (
            <button
              onClick={stopListening}
              className="p-2 bg-red-500 rounded-full transition-all animate-pulse"
              title="Stop listening"
            >
              <Square className="w-5 h-5 text-white" fill="white" />
            </button>
          ) : (
            <button
              onClick={startListening}
              disabled={isLoading}
              className="disabled:opacity-30 transition-opacity p-2 hover:bg-gray-100 rounded-full"
              title="Voice input (click to speak)"
            >
              <Mic className="w-6 h-6 text-gray-600" />
            </button>
          )}
          <button
            onClick={handleSubmit}
            disabled={!input.trim() || isLoading || isListening}
            className="disabled:opacity-30 transition-opacity"
          >
            <Send 
              className="w-6 h-6 text-blue-500" 
              fill={input.trim() && !isLoading && !isListening ? '#3b82f6' : 'none'} 
            />
          </button>
        </div>
      </div>

      {/* Hidden audio element for TTS playback */}
      <audio ref={audioRef} style={{ display: 'none' }} />
    </div>
  );
}

