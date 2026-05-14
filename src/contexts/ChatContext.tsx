import React, { createContext, useContext, useEffect, useState, ReactNode } from "react";

import { clearChatSession, sendChatMessage } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";
import { useAuth } from "@/contexts/AuthContext";

interface ChatContextType {
  messages: ChatMessage[];
  isLoading: boolean;
  sendMessage: (text: string) => Promise<void>;
  clearChat: () => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const ChatProvider = ({ children }: { children: ReactNode }) => {
  const { user } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    setMessages([]);
  }, [user?.id]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return;

    setIsLoading(true);
    setMessages(prev => [
      ...prev,
      { role: "user", content: text },
      { role: "assistant", content: "", toolCalls: [], status: "Analyzing your request..." },
    ]);

    try {
      const response = await sendChatMessage(text, user?.id);
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error("No reader available");
      }

      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() ?? "";

        for (const eventChunk of events) {
          const event = parseSseEvent(eventChunk);
          if (!event) continue;
          applyStreamEvent(event, setMessages);
        }
      }
    } catch (error) {
      updateLatestAssistantMessage(setMessages, message => ({
        ...message,
        status: undefined,
        content: error instanceof Error ? error.message : "There was an error reaching the agent.",
      }));
    } finally {
      setIsLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([]);
    void clearChatSession(user?.id).catch(console.error);
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
    throw new Error("useChat must be used within a ChatProvider");
  }
  return context;
};

function parseSseEvent(rawEvent: string): Record<string, unknown> | null {
  const dataLines = rawEvent
    .split(/\r?\n/)
    .filter(line => line.startsWith("data:"))
    .map(line => line.slice(5).trim());

  if (dataLines.length === 0) {
    return null;
  }

  try {
    return JSON.parse(dataLines.join(""));
  } catch (error) {
    console.error("Error parsing stream event:", error);
    return null;
  }
}

function applyStreamEvent(
  event: Record<string, unknown>,
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>,
) {
  switch (event.type) {
    case "status":
    case "warning":
      updateLatestAssistantMessage(setMessages, message => ({
        ...message,
        status: typeof event.content === "string" ? event.content : message.status,
      }));
      return;
    case "message":
      updateLatestAssistantMessage(setMessages, message => ({
        ...message,
        content: `${message.content}${typeof event.content === "string" ? event.content : ""}`,
      }));
      return;
    case "tool_call":
      updateLatestAssistantMessage(setMessages, message => ({
        ...message,
        toolCalls: [
          ...(message.toolCalls ?? []),
          {
            callId: String(event.call_id ?? `${Date.now()}`),
            name: String(event.name ?? "tool"),
            status: "running",
            summary: "Running tool...",
            arguments: isRecord(event.arguments) ? event.arguments : undefined,
          },
        ],
      }));
      return;
    case "tool_result":
      updateLatestAssistantMessage(setMessages, message => ({
        ...message,
        toolCalls: (message.toolCalls ?? []).map(trace =>
          trace.callId === String(event.call_id)
            ? {
                ...trace,
                status: event.ok ? "success" : "error",
                summary: String(event.summary ?? trace.summary),
                result: event.result,
              }
            : trace,
        ),
      }));
      return;
    case "done":
      updateLatestAssistantMessage(setMessages, message => ({
        ...message,
        status: undefined,
      }));
      return;
    default:
      return;
  }
}

function updateLatestAssistantMessage(
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>,
  updater: (message: ChatMessage) => ChatMessage,
) {
  setMessages(prev => {
    const next = [...prev];
    for (let index = next.length - 1; index >= 0; index -= 1) {
      if (next[index].role === "assistant") {
        next[index] = updater({
          ...next[index],
          toolCalls: next[index].toolCalls ? [...next[index].toolCalls] : [],
        });
        break;
      }
    }
    return next;
  });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
