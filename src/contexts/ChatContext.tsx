import React, { createContext, useContext, useState, ReactNode } from 'react';
import { sendChatMessage } from '@/lib/api';

export interface Message {
  role: "user" | "assistant";
  content: string;
  thought?: string;
  toolCalls?: { tool: string, output: unknown }[];
}

interface ChatContextType {
  messages: Message[];
  isLoading: boolean;
  sendMessage: (text: string) => Promise<void>;
  clearChat: () => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const ChatProvider = ({ children }: { children: ReactNode }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return;
    
    // 1. Add user message
    const userMsg: Message = { role: "user", content: text };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    // 2. Add initial empty assistant message for streaming
    const assistantMsg: Message = { role: "assistant", content: "", toolCalls: [] };
    setMessages(prev => [...prev, assistantMsg]);

    try {
      const response = await sendChatMessage(text);
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error("No reader available");

      let accumulatedContent = "";
      let accumulatedThought = "";
      let toolCalls: { tool: string, output: unknown }[] = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n").filter(l => l.trim());

        for (const line of lines) {
          try {
            const data = JSON.parse(line);
            if (data.type === "thought") {
              accumulatedThought = data.content;
            } else if (data.type === "content") {
              accumulatedContent += data.content;
            } else if (data.type === "tool") {
              toolCalls.push({ tool: data.name, output: data.args });
            }

            // Update the last message in state
            setMessages(prev => {
              const newMessages = [...prev];
              const lastMsg = newMessages[newMessages.length - 1];
              lastMsg.content = accumulatedContent;
              lastMsg.thought = accumulatedThought;
              lastMsg.toolCalls = toolCalls;
              return newMessages;
            });
          } catch (e) {
            console.error("Error parsing stream chunk:", e);
          }
        }
      }
    } catch (e) {
      setMessages(prev => {
        const newMessages = [...prev];
        if (newMessages.length > 0) {
          newMessages[newMessages.length - 1].content = "There was an error reaching the agent.";
        }
        return newMessages;
      });
    } finally {
      setIsLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([]);
  };

  return (
    <ChatContext.Provider value={{ messages, isLoading, sendMessage, clearChat }}>
      {children}
    </ChatContext.Provider>
  );
};

export const useChat = () => {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
};
