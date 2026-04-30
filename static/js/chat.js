/**
 * 聊天模块
 *
 * 处理聊天逻辑、SSE 流式接收。
 * 使用 requestAnimationFrame 批处理 DOM 更新，确保流式输出丝滑。
 */

const ChatManager = {
    _abortController: null,
    isStreaming: false,
    _pendingChunks: '',
    _fullContent: '',
    _contentEl: null,
    _rafId: null,
    _isNearBottom: true,
    _currentMessage: '',
    _sessionId: null,

    /**
     * 发送消息
     */
    async sendMessage(message, sessionId) {
        if (this.isStreaming || !message.trim()) {
            return;
        }

        this._currentMessage = message;
        this._sessionId = sessionId;

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

        // 切换按钮
        App.showStopButton();

        try {
            await this.streamChat(message, sessionId, contentEl);
        } catch (error) {
            if (error.name === 'AbortError') {
                // 用户主动停止
                if (contentEl) {
                    contentEl.innerHTML = renderMarkdown(this._fullContent) +
                        '<br><em style="color: var(--text-muted);">[已停止生成]</em>';
                }
                App.setStatus('ready', '已停止');
            } else {
                console.error('发送消息失败:', error);
                contentEl.textContent = '发送失败: ' + error.message;
                App.setStatus('error', '发送失败');
            }
        } finally {
            this.isStreaming = false;
            App.updateMessageCount();
            App.showSendButton();
        }
    },

    /**
     * SSE 流式聊天（rAF 批处理版本）
     */
    async streamChat(message, sessionId, contentEl) {
        this._contentEl = contentEl;
        this._fullContent = '';
        this._pendingChunks = '';
        this._isNearBottom = true;
        this._abortController = new AbortController();

        const response = await fetch('/api/chat/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                session_id: sessionId,
                stream: true
            }),
            signal: this._abortController.signal
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        // 标记流式状态，显示光标
        contentEl.classList.add('streaming');
        contentEl.innerHTML = '';

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let lineBuffer = '';
        let receivedSessionId = null;

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                lineBuffer += decoder.decode(value, { stream: true });
                const lines = lineBuffer.split('\n');
                lineBuffer = lines.pop(); // 保留不完整的最后一行

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
                                    // 只累积，不碰 DOM
                                    this._pendingChunks += data.content;
                                    this._fullContent += data.content;
                                    this._scheduleRender();
                                    break;

                                case 'summary':
                                    console.log('对话已自动总结');
                                    break;

                                case 'done':
                                    // 最终渲染
                                    this._flushFinalRender();
                                    // 保存到本地记忆
                                    if (receivedSessionId) {
                                        MemoryManager.addMessage(receivedSessionId, 'user', message);
                                        MemoryManager.addMessage(receivedSessionId, 'assistant', this._fullContent);
                                        App.refreshHistory();
                                    }
                                    App.setStatus('ready', '就绪');
                                    break;

                                case 'error':
                                    if (contentEl) {
                                        contentEl.textContent = '错误: ' + data.message;
                                    }
                                    App.setStatus('error', '发生错误');
                                    break;
                            }
                        } catch (e) {
                            console.error('解析 SSE 数据失败:', e);
                        }
                    }
                }
            }
        } finally {
            // 确保清理
            if (contentEl) {
                contentEl.classList.remove('streaming');
            }
        }
    },

    /**
     * 调度 rAF 渲染（每帧最多一次）
     */
    _scheduleRender() {
        if (this._rafId) return;
        this._rafId = requestAnimationFrame(() => this._renderFrame());
    },

    /**
     * rAF 回调：批量渲染累积的 chunks
     */
    _renderFrame() {
        this._rafId = null;
        if (!this._contentEl) return;

        // 只在有新内容时渲染
        if (!this._pendingChunks) return;

        this._contentEl.innerHTML = renderMarkdown(this._fullContent);
        this._pendingChunks = '';

        if (this._isNearBottom) {
            // 延迟到下一帧滚动，避免布局抖动
            requestAnimationFrame(() => App.scrollToBottom());
        }
    },

    /**
     * 最终渲染：确保完整输出
     */
    _flushFinalRender() {
        if (this._rafId) {
            cancelAnimationFrame(this._rafId);
            this._rafId = null;
        }
        if (!this._contentEl) return;
        this._contentEl.innerHTML = renderMarkdown(this._fullContent);
        this._contentEl.classList.remove('streaming');
        App.scrollToBottom();
    },

    /**
     * 停止流式响应
     */
    stopStreaming() {
        if (this._abortController) {
            this._abortController.abort();
            this._abortController = null;
        }
        this.isStreaming = false;
        if (this._rafId) {
            cancelAnimationFrame(this._rafId);
            this._rafId = null;
        }
    },

    /**
     * 兼容旧接口：formatContent
     */
    formatContent(content) {
        return renderMarkdown(content);
    }
};

/**
 * Markdown 渲染（使用 marked.js）
 * 流式安全：自动处理未闭合的代码围栏
 */
let _markedConfigured = false;

function renderMarkdown(text) {
    if (!text) return '';

    // 流式安全：未闭合的代码围栏补全
    const fenceCount = (text.match(/```/g) || []).length;
    let safe = text;
    if (fenceCount % 2 !== 0) {
        safe += '\n```';
    }

    // 检查 marked 是否可用
    if (typeof marked !== 'undefined') {
        // 只配置一次
        if (!_markedConfigured) {
            _markedConfigured = true;
            // marked v5+ 推荐 use()，兼容旧版 setOptions
            if (typeof marked.use === 'function') {
                marked.use({ breaks: true, gfm: true });
            } else if (typeof marked.setOptions === 'function') {
                marked.setOptions({ breaks: true, gfm: true });
            }
        }
        return marked.parse(safe);
    }

    // fallback：基础格式化
    let formatted = safe
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    formatted = formatted.replace(/```(\w*)\n([\s\S]*?)```/g, (match, lang, code) => {
        return `<pre><code class="language-${lang}">${code.trim()}</code></pre>`;
    });
    formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
    formatted = formatted.replace(/\n/g, '<br>');
    return formatted;
}

// 导出
window.ChatManager = ChatManager;
window.renderMarkdown = renderMarkdown;
