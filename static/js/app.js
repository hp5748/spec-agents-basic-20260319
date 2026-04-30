/**
 * 主应用模块
 *
 * 初始化和管理 UI 交互。
 */

const App = {
    elements: {},
    sessionId: null,

    /**
     * 初始化应用
     */
    init() {
        this.cacheElements();
        this.bindEvents();
        this.setupScrollTracking();
        this.loadSession();
        this.refreshHistory();
    },

    /**
     * 缓存 DOM 元素
     */
    cacheElements() {
        this.elements = {
            chatMessages: document.getElementById('chat-messages'),
            userInput: document.getElementById('user-input'),
            sendBtn: document.getElementById('send-btn'),
            stopBtn: document.getElementById('stop-btn'),
            newChatBtn: document.getElementById('new-chat'),
            clearHistoryBtn: document.getElementById('clear-history'),
            sessionIdEl: document.getElementById('session-id'),
            statusEl: document.getElementById('status'),
            messageCountEl: document.getElementById('message-count'),
            historyList: document.getElementById('history-list')
        };
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        // 发送按钮
        this.elements.sendBtn.addEventListener('click', () => this.handleSend());

        // 停止按钮
        this.elements.stopBtn.addEventListener('click', () => ChatManager.stopStreaming());

        // 回车发送
        this.elements.userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSend();
            }
        });

        // 自动调整输入框高度
        this.elements.userInput.addEventListener('input', () => {
            this.elements.userInput.style.height = 'auto';
            this.elements.userInput.style.height =
                Math.min(this.elements.userInput.scrollHeight, 150) + 'px';
        });

        // 新建对话
        this.elements.newChatBtn.addEventListener('click', () => this.newChat());

        // 清空历史
        this.elements.clearHistoryBtn.addEventListener('click', () => this.clearHistory());

        // 历史列表：事件委托（替代逐项绑定）
        this.elements.historyList.addEventListener('click', (e) => {
            const item = e.target.closest('.history-item');
            if (item) {
                this.loadSessionById(item.dataset.sessionId);
            }
        });
    },

    /**
     * 设置智能滚动追踪
     * 用户上滚时不强制拉回底部
     */
    setupScrollTracking() {
        const el = this.elements.chatMessages;
        el.addEventListener('scroll', () => {
            ChatManager._isNearBottom = this.isNearBottom();
        }, { passive: true });
    },

    /**
     * 判断用户是否在底部附近
     */
    isNearBottom(threshold = 80) {
        const el = this.elements.chatMessages;
        return el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
    },

    /**
     * 加载会话
     */
    loadSession() {
        let session = MemoryManager.getCurrentSession();

        if (!session) {
            // 创建新会话
            const newSessionId = MemoryManager.createSession();
            this.sessionId = newSessionId;
            session = MemoryManager.getSession(newSessionId);
        } else {
            this.sessionId = session.id;
        }

        // 更新 UI
        this.setSessionId(this.sessionId);

        // 恢复历史消息
        if (session && session.messages.length > 0) {
            // 清空欢迎消息
            this.elements.chatMessages.innerHTML = '';

            // 显示历史消息
            session.messages.forEach(msg => {
                this.addMessage(msg.role, msg.content, false);
            });

            this.scrollToBottom();
        }

        this.updateMessageCount();
    },

    /**
     * 处理发送
     */
    handleSend() {
        const message = this.elements.userInput.value.trim();
        if (!message || ChatManager.isStreaming) return;

        // 清空输入
        this.elements.userInput.value = '';
        this.elements.userInput.style.height = 'auto';

        // 发送消息
        ChatManager.sendMessage(message, this.sessionId);
    },

    /**
     * 添加消息到聊天区
     */
    addMessage(role, content, scroll = true) {
        // 移除欢迎消息
        const welcome = this.elements.chatMessages.querySelector('.welcome-message');
        if (welcome) {
            welcome.remove();
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = renderMarkdown(content) || content;

        messageDiv.appendChild(contentDiv);
        this.elements.chatMessages.appendChild(messageDiv);

        if (scroll) {
            this.scrollToBottom();
        }

        return messageDiv;
    },

    /**
     * 滚动到底部
     */
    scrollToBottom() {
        const el = this.elements.chatMessages;
        el.scrollTop = el.scrollHeight;
    },

    /**
     * 设置会话 ID
     */
    setSessionId(sessionId) {
        this.sessionId = sessionId;
        this.elements.sessionIdEl.textContent = sessionId.substring(0, 16) + '...';
        MemoryManager.setCurrentSessionId(sessionId);
    },

    /**
     * 设置状态
     */
    setStatus(type, text) {
        this.elements.statusEl.textContent = text;
        this.elements.statusEl.className = 'status ' + type;
    },

    /**
     * 更新消息计数
     */
    updateMessageCount() {
        const session = MemoryManager.getCurrentSession();
        const count = session ? session.messages.length : 0;
        this.elements.messageCountEl.textContent = `${count} 条消息`;
    },

    /**
     * 显示停止按钮（隐藏发送按钮）
     */
    showStopButton() {
        this.elements.sendBtn.style.display = 'none';
        this.elements.stopBtn.style.display = 'flex';
    },

    /**
     * 显示发送按钮（隐藏停止按钮）
     */
    showSendButton() {
        this.elements.sendBtn.style.display = 'flex';
        this.elements.stopBtn.style.display = 'none';
    },

    /**
     * 流式结束回调
     */
    onStreamEnd() {
        this.showSendButton();
    },

    /**
     * 新建对话
     */
    newChat() {
        // 清空聊天区
        this.elements.chatMessages.innerHTML = `
            <div class="welcome-message">
                <h2>欢迎使用 Super Agent</h2>
                <p>我可以帮助你完成各种任务，包括：</p>
                <ul>
                    <li>SQLite 数据库查询</li>
                    <li>信息检索和分析</li>
                    <li>对话问答</li>
                </ul>
                <p class="hint">输入消息开始对话...</p>
            </div>
        `;

        // 创建新会话
        const newSessionId = MemoryManager.createSession();
        this.setSessionId(newSessionId);
        this.updateMessageCount();
        this.refreshHistory();
    },

    /**
     * 刷新历史列表（事件委托模式，不再逐项绑定）
     */
    refreshHistory() {
        const sessions = MemoryManager.getSessionList();
        const currentId = this.sessionId;

        this.elements.historyList.innerHTML = sessions.map(session => {
            const preview = MemoryManager.getSessionPreview(session);
            const isActive = session.id === currentId ? 'active' : '';

            return `
                <div class="history-item ${isActive}"
                     data-session-id="${session.id}"
                     title="${preview}">
                    ${preview}
                </div>
            `;
        }).join('');
    },

    /**
     * 加载指定会话
     */
    loadSessionById(sessionId) {
        const session = MemoryManager.getSession(sessionId);
        if (!session) return;

        this.sessionId = sessionId;
        this.setSessionId(sessionId);

        // 清空聊天区
        this.elements.chatMessages.innerHTML = '';

        // 显示历史消息
        session.messages.forEach(msg => {
            this.addMessage(msg.role, msg.content, false);
        });

        this.scrollToBottom();
        this.updateMessageCount();
        this.refreshHistory();
    },

    /**
     * 清空历史
     */
    clearHistory() {
        if (confirm('确定要清空所有对话历史吗？')) {
            MemoryManager.clearAll();
            this.newChat();
            this.refreshHistory();
        }
    }
};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});
