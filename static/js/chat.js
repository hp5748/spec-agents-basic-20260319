/**
 * 聊天模块
 *
 * 处理聊天逻辑、SSE 流式接收。
 */

const ChatManager = {
    eventSource: null,
    isStreaming: false,

    /**
     * 发送消息
     */
    async sendMessage(message, sessionId) {
        if (this.isStreaming || !message.trim()) {
            return;
        }

        // 显示用户消息
        App.addMessage('user', message);

        // 显示助手消息占位
        const assistantMsgEl = App.addMessage('assistant', '');
        const contentEl = assistantMsgEl.querySelector('.message-content');

        // 显示加载动画
        contentEl.innerHTML = `
            <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;

        // 更新状态
        App.setStatus('streaming', '正在响应...');
        this.isStreaming = true;

        try {
            // 使用 SSE 流式接收
            await this.streamChat(message, sessionId, contentEl);
        } catch (error) {
            console.error('发送消息失败:', error);
            contentEl.textContent = '发送失败: ' + error.message;
            App.setStatus('error', '发送失败');
        } finally {
            this.isStreaming = false;
            App.updateMessageCount();
        }
    },

    /**
     * SSE 流式聊天
     */
    async streamChat(message, sessionId, contentEl) {
        const response = await fetch('/api/chat/stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId,
                stream: true
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullContent = '';
        let receivedSessionId = null;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));

                        switch (data.type) {
                            case 'start':
                                receivedSessionId = data.session_id;
                                App.setSessionId(receivedSessionId);
                                break;

                            case 'content':
                                fullContent += data.content;
                                contentEl.innerHTML = this.formatContent(fullContent);
                                App.scrollToBottom();
                                break;

                            case 'summary':
                                // 对话被总结
                                console.log('对话已自动总结');
                                break;

                            case 'done':
                                // 保存到本地记忆
                                if (receivedSessionId) {
                                    MemoryManager.addMessage(receivedSessionId, 'user', message);
                                    MemoryManager.addMessage(receivedSessionId, 'assistant', fullContent);
                                    App.refreshHistory();
                                }
                                App.setStatus('ready', '就绪');
                                break;

                            case 'error':
                                contentEl.textContent = '错误: ' + data.message;
                                App.setStatus('error', '发生错误');
                                break;
                        }
                    } catch (e) {
                        console.error('解析 SSE 数据失败:', e);
                    }
                }
            }
        }
    },

    /**
     * 格式化消息内容
     */
    formatContent(content) {
        // 转义 HTML
        let formatted = content
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');

        // 代码块
        formatted = formatted.replace(/```(\w*)\n([\s\S]*?)```/g, (match, lang, code) => {
            return `<pre><code class="language-${lang}">${code.trim()}</code></pre>`;
        });

        // 行内代码
        formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');

        // 换行
        formatted = formatted.replace(/\n/g, '<br>');

        return formatted;
    },

    /**
     * 停止流式响应
     */
    stopStreaming() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
        this.isStreaming = false;
    }
};

// 导出
window.ChatManager = ChatManager;
