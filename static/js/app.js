/**
 * app.js - 前端交互逻辑（角色 C）
 *
 * 功能：API 请求封装、页面导航、表单处理、数据展示、动画控制。
 */

// ============================================
// 全局配置
// ============================================
const API_BASE = '';
let currentUser = JSON.parse(localStorage.getItem('currentUser')) || null;

// ============================================
// API 请求封装
// ============================================
async function apiRequest(url, options = {}) {
    const response = await fetch(url, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    });
    const data = await response.json();
    if (!data.success) {
        throw new Error(data.error || '请求失败');
    }
    return data;
}

// GET 请求
async function apiGet(url) {
    return apiRequest(url, { method: 'GET' });
}

// POST 请求
async function apiPost(url, body) {
    return apiRequest(url, {
        method: 'POST',
        body: JSON.stringify(body),
    });
}

// PUT 请求
async function apiPut(url, body) {
    return apiRequest(url, {
        method: 'PUT',
        body: JSON.stringify(body),
    });
}

// DELETE 请求
async function apiDelete(url) {
    return apiRequest(url, { method: 'DELETE' });
}

// ============================================
// 用户管理
// ============================================
async function createUser(userData) {
    const result = await apiPost('/api/user', userData);
    currentUser = result.user;
    localStorage.setItem('currentUser', JSON.stringify(currentUser));
    return currentUser;
}

async function getUser(userId) {
    const result = await apiGet(`/api/user/${userId}`);
    return result.user;
}

async function updateUser(userId, updates) {
    const result = await apiPut(`/api/user/${userId}`, updates);
    currentUser = result.user;
    localStorage.setItem('currentUser', JSON.stringify(currentUser));
    return currentUser;
}

// ============================================
// 饮食记录
// ============================================
async function getRecords(userId, filters = {}) {
    const params = new URLSearchParams({ user_id: userId, ...filters });
    const result = await apiGet(`/api/records?${params}`);
    return result.records;
}

async function createRecord(recordData) {
    return apiPost('/api/records', recordData);
}

async function updateRecord(recordId, updates) {
    return apiPut(`/api/records/${recordId}`, updates);
}

async function deleteRecord(recordId) {
    return apiDelete(`/api/records/${recordId}`);
}

// ============================================
// 看板数据
// ============================================
async function getDashboard(userId) {
    return apiGet(`/api/dashboard/${userId}`);
}

async function getNutrition(userId) {
    return apiGet(`/api/nutrition/${userId}`);
}

async function getBudget(userId) {
    return apiGet(`/api/budget/${userId}`);
}

// ============================================
// 推荐
// ============================================
async function getRecommendations(userId, meal = '午餐', canteen = '') {
    const params = new URLSearchParams({ meal, canteen });
    return apiGet(`/api/recommend/${userId}?${params}`);
}

// ============================================
// 导出
// ============================================
function exportPDF(userId) {
    window.open(`/api/export/${userId}`, '_blank');
}

// ============================================
// UI 工具函数
// ============================================
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.5s';
        setTimeout(() => toast.remove(), 500);
    }, 3000);
}

function showLoading(element) {
    element.innerHTML = '<div class="loading"></div> 加载中...';
    element.disabled = true;
}

function hideLoading(element, originalText) {
    element.innerHTML = originalText;
    element.disabled = false;
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleDateString('zh-CN');
}

function formatMoney(amount) {
    return Number(amount).toFixed(2);
}

// ============================================
// 页面导航
// ============================================
function setupNavigation() {
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
}

// ============================================
// 表单验证
// ============================================
function validateForm(formData, rules) {
    const errors = [];
    for (const [field, rule] of Object.entries(rules)) {
        const value = formData[field];
        if (rule.required && (!value || value === '')) {
            errors.push(`${rule.label || field}不能为空`);
        }
        if (rule.min !== undefined && value < rule.min) {
            errors.push(`${rule.label || field}不能小于${rule.min}`);
        }
        if (rule.max !== undefined && value > rule.max) {
            errors.push(`${rule.label || field}不能大于${rule.max}`);
        }
    }
    return errors;
}

// ============================================
// 初始化
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    setupNavigation();

    // 全局错误处理
    window.addEventListener('error', (e) => {
        console.error('JavaScript error:', e.error);
        showToast('页面发生错误，请刷新重试', 'error');
    });

    // 未处理 Promise 错误
    window.addEventListener('unhandledrejection', (e) => {
        console.error('Unhandled promise rejection:', e.reason);
        showToast('请求失败，请检查网络连接', 'error');
    });
});

// 导出全局函数供页面脚本使用
window.AppAPI = {
    createUser, getUser, updateUser,
    getRecords, createRecord, updateRecord, deleteRecord,
    getDashboard, getNutrition, getBudget,
    getRecommendations, exportPDF,
    showToast, showLoading, hideLoading,
    formatDate, formatMoney, validateForm,
    currentUser
};
