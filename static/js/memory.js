/**
 * 记忆管理模块
 *
 * 负责在浏览器端管理对话历史，使用 localStorage 存储。
 */

const MemoryManager = {
    STORAGE_KEY: 'super_agent_sessions',
    CURRENT_SESSION_KEY: 'super_agent_current_session',
    MAX_HISTORY_ITEMS: 50,

    /**
     * 获取所有会话
     */
    getSessions() {
        try {
            const data = localStorage.getItem(this.STORAGE_KEY);
            return data ? JSON.parse(data) : {};
        } catch (e) {
            console.error('读取会话失败:', e);
            return {};
        }
    },

    /**
     * 保存所有会话
     */
    saveSessions(sessions) {
        try {
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(sessions));
        } catch (e) {
            console.error('保存会话失败:', e);
        }
    },

    /**
     * 获取当前会话 ID
     */
    getCurrentSessionId() {
        return localStorage.getItem(this.CURRENT_SESSION_KEY) || null;
    },

    /**
     * 设置当前会话 ID
     */
    setCurrentSessionId(sessionId) {
        localStorage.setItem(this.CURRENT_SESSION_KEY, sessionId);
    },

    /**
     * 创建新会话
     */
    createSession() {
        const sessionId = this.generateSessionId();
        const sessions = this.getSessions();

        sessions[sessionId] = {
            id: sessionId,
            messages: [],
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString()
        };

        // 清理旧会话
        this.cleanupOldSessions(sessions);

        this.saveSessions(sessions);
        this.setCurrentSessionId(sessionId);

        return sessionId;
    },

    /**
     * 生成会话 ID
     */
    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    },

    /**
     * 获取会话
     */
    getSession(sessionId) {
        const sessions = this.getSessions();
        return sessions[sessionId] || null;
    },

    /**
     * 获取当前会话
     */
    getCurrentSession() {
        const sessionId = this.getCurrentSessionId();
        if (!sessionId) {
            return null;
        }
        return this.getSession(sessionId);
    },

    /**
     * 添加消息到会话
     */
    addMessage(sessionId, role, content) {
        const sessions = this.getSessions();

        if (!sessions[sessionId]) {
            sessions[sessionId] = {
                id: sessionId,
                messages: [],
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString()
            };
        }

        sessions[sessionId].messages.push({
            role: role,
            content: content,
            timestamp: new Date().toISOString()
        });

        sessions[sessionId].updatedAt = new Date().toISOString();

        // 清理旧会话
        this.cleanupOldSessions(sessions);

        this.saveSessions(sessions);
    },

    /**
     * 获取会话消息
     */
    getMessages(sessionId) {
        const session = this.getSession(sessionId);
        return session ? session.messages : [];
    },

    /**
     * 清除会话
     */
    clearSession(sessionId) {
        const sessions = this.getSessions();
        delete sessions[sessionId];
        this.saveSessions(sessions);

        if (this.getCurrentSessionId() === sessionId) {
            localStorage.removeItem(this.CURRENT_SESSION_KEY);
        }
    },

    /**
     * 清除所有会话
     */
    clearAll() {
        localStorage.removeItem(this.STORAGE_KEY);
        localStorage.removeItem(this.CURRENT_SESSION_KEY);
    },

    /**
     * 获取会话列表（按更新时间排序）
     */
    getSessionList() {
        const sessions = this.getSessions();
        return Object.values(sessions).sort((a, b) => {
            return new Date(b.updatedAt) - new Date(a.updatedAt);
        });
    },

    /**
     * 获取会话预览（用于历史列表）
     */
    getSessionPreview(session) {
        if (!session || !session.messages || session.messages.length === 0) {
            return '空会话';
        }

        // 获取第一条用户消息作为预览
        const firstUserMsg = session.messages.find(m => m.role === 'user');
        if (firstUserMsg) {
            return firstUserMsg.content.substring(0, 50) + (firstUserMsg.content.length > 50 ? '...' : '');
        }

        return '对话';
    },

    /**
     * 清理旧会话
     */
    cleanupOldSessions(sessions) {
        const sessionList = Object.values(sessions).sort((a, b) => {
            return new Date(b.updatedAt) - new Date(a.updatedAt);
        });

        if (sessionList.length > this.MAX_HISTORY_ITEMS) {
            const toRemove = sessionList.slice(this.MAX_HISTORY_ITEMS);
            toRemove.forEach(session => {
                delete sessions[session.id];
            });
        }
    },

    /**
     * 同步服务端会话
     */
    async syncFromServer(sessionId) {
        try {
            const response = await fetch(`/api/session/${sessionId}`);
            if (response.ok) {
                const data = await response.json();
                const sessions = this.getSessions();

                sessions[sessionId] = {
                    id: sessionId,
                    messages: data.messages,
                    createdAt: data.created_at || new Date().toISOString(),
                    updatedAt: new Date().toISOString()
                };

                this.saveSessions(sessions);
                return data;
            }
        } catch (e) {
            console.error('同步服务端会话失败:', e);
        }
        return null;
    }
};

// 导出
window.MemoryManager = MemoryManager;
