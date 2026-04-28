import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Loader2, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useChat } from "@/contexts/ChatContext";


export default function Chat() {
  const { messages, isLoading, sendMessage } = useChat();
  const [input, setInput] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const onSend = async (text?: string) => {
    const query = text ?? input.trim();
    if (!query || isLoading) return;
    setInput("");
    await sendMessage(query);
  };

  const suggestions = [
    "Show all products",
    "Show out-of-stock products",
    "What is the cheapest product?",
    "Show products in Computers category",
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-7rem)] animate-slide-in">
      <div className="flex-1 overflow-auto space-y-6 pb-4 scrollbar-thin">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center px-4">
            <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
              <Sparkles className="w-8 h-8 text-primary" />
            </div>
            <h3 className="text-lg font-semibold text-foreground mb-1">Stock Intelligence Agent</h3>
            <p className="text-sm text-muted-foreground mb-6 max-w-md">
              I can answer verified inventory questions and show which tools were used to produce each response.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-lg w-full">
              {suggestions.map(suggestion => (
                <button
                  key={suggestion}
                  onClick={() => onSend(suggestion)}
                  className="text-left text-sm px-3 py-2.5 rounded-lg border border-border bg-card hover:bg-muted transition-colors text-foreground"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message, index) => (
          <div key={index} className={`flex gap-3 ${message.role === "user" ? "justify-end" : ""}`}>
            {message.role === "assistant" && (
              <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0 mt-0.5 border border-primary/20">
                <Bot className="w-4 h-4 text-primary" />
              </div>
            )}

            <div className={`max-w-[85%] ${message.role === "user" ? "bg-primary text-primary-foreground rounded-2xl rounded-br-md px-4 py-2.5 shadow-md shadow-primary/10" : ""}`}>
              {message.role === "assistant" ? (
                <div className="space-y-3">
                  {message.toolCalls && message.toolCalls.length > 0 && (
                    <div className="space-y-2">
                      {message.toolCalls.map(tool => (
                        <div key={tool.callId} className="rounded-xl border border-border bg-card/70 px-3 py-2">
                          <div className="flex items-center justify-between gap-3">
                            <p className="text-xs font-semibold text-foreground">{formatToolName(tool.name)}</p>
                            <span
                              className={`text-[11px] font-medium ${
                                tool.status === "running"
                                  ? "text-muted-foreground"
                                  : tool.status === "success"
                                  ? "text-success"
                                  : "text-destructive"
                              }`}
                            >
                              {tool.status === "running" ? "Running" : tool.status === "success" ? "Verified" : "Error"}
                            </span>
                          </div>
                          <p className="mt-1 text-xs text-muted-foreground">{tool.summary}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  {message.status && (
                    <p className="text-xs font-medium text-muted-foreground">{message.status}</p>
                  )}

                  <div
                    className="text-sm text-foreground prose prose-sm max-w-none leading-relaxed"
                    dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }}
                  />
                </div>
              ) : (
                <p className="text-sm">{message.content}</p>
              )}
            </div>

            {message.role === "user" && (
              <div className="w-8 h-8 rounded-lg bg-secondary flex items-center justify-center shrink-0 mt-0.5 border border-border">
                <User className="w-4 h-4 text-secondary-foreground" />
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0 border border-primary/20">
              <Bot className="w-4 h-4 text-primary" />
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground italic">
              <Loader2 className="w-4 h-4 animate-spin" />
              Processing database query...
            </div>
          </div>
        )}

        <div ref={endRef} />
      </div>

      <div className="border-t border-border pt-4 pb-2">
        <form
          onSubmit={event => {
            event.preventDefault();
            void onSend();
          }}
          className="flex gap-2"
        >
          <input
            value={input}
            onChange={event => setInput(event.target.value)}
            placeholder="Ask about inventory, categories, stock levels, or cheapest items..."
            className="flex-1 px-4 py-3 rounded-xl border border-input bg-card text-sm text-foreground shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
          />
          <Button
            type="submit"
            disabled={!input.trim() || isLoading}
            size="icon"
            className="shrink-0 w-11 h-11 rounded-xl shadow-lg shadow-primary/20"
          >
            <Send className="w-4.5 h-4.5" />
          </Button>
        </form>
      </div>
    </div>
  );
}


function renderMarkdown(markdown: string): string {
  return markdown
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n\n/g, "<br/><br/>")
    .replace(/\n- /g, "<br/>- ")
    .replace(/\n/g, "<br/>");
}


function formatToolName(name: string): string {
  return name
    .split("_")
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
