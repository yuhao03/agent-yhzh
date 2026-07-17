"use client";

import {
  CopilotSidebar,
  useConfigureSuggestions,
} from "@copilotkit/react-core/v2";
import { MessageCircleMore } from "lucide-react";

export function UserAssistant() {
  useConfigureSuggestions({
    suggestions: [
      { title: "方案分析", message: "帮我分析一个业务方案是否合理" },
      { title: "问题诊断", message: "我遇到一个问题，帮我定位可能原因" },
      { title: "补充反馈", message: "我想纠正上一条回答" },
    ],
    available: "before-first-message",
  });

  return (
    <div className="assistant-card">
      <div>
        <MessageCircleMore color="#147a52" size={26} />
        <h3>智能助手已准备好</h3>
        <p>可以先从一个具体的业务问题开始。</p>
        <div className="assistant-suggestions">
          <span>帮我梳理一个解决方案</span>
          <span>解释一下这个概念</span>
          <span>我来纠正一条回答</span>
        </div>
      </div>
      <CopilotSidebar
        defaultOpen={false}
        labels={{
          modalHeaderTitle: "砺知智能助手",
          welcomeMessageText: "你好，我会基于已经确认的信息帮助你。你想解决什么问题？",
          chatInputPlaceholder: "输入你的问题或反馈…",
          chatDisclaimerText: "回答可能不完整，重要信息请结合实际情况确认。",
        }}
      />
      <div className="open-assistant-button">点击页面右下角对话按钮开始</div>
    </div>
  );
}
