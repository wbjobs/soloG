<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { connectSSE, disconnectSSE, loadNotifications, unreadCount } from '$lib/stores/notifications';
  import { PUBLIC_POCKETBASE_URL } from '$env/static/public';

  let user: typeof $page.data.user = null;

  $: if ($page.data) {
    user = $page.data.user;
  }

  onMount(() => {
    if (user) {
      connectSSE();
      loadNotifications();
    }
    return () => disconnectSSE();
  });

  $: if (user) {
    connectSSE();
    loadNotifications();
  } else {
    disconnectSSE();
  }
</script>

<div class="app">
  <nav class="navbar">
    <div class="nav-brand">
      <a href="/">📋 工单协同系统</a>
    </div>
    <div class="nav-links">
      {#if user}
        <a href="/tickets">工单列表</a>
        <a href="/kanban">看板视图</a>
        <a href="/reports/time">工时报表</a>
        <a href="/tickets/new">新建工单</a>
        <div class="nav-user">
          <span class="unread-badge" hidden={$unreadCount === 0}>{$unreadCount}</span>
          <span>{user.name}</span>
          <form method="post" action="/api/auth/logout" style="display: inline;">
            <button type="submit" class="btn-logout">退出</button>
          </form>
        </div>
      {:else}
        <a href="/login">登录</a>
      {/if}
    </div>
  </nav>

  <main class="main-content">
    <slot />
  </main>
</div>

<style>
  .app {
    min-height: 100vh;
    background: #f5f7fa;
  }

  .navbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 24px;
    height: 60px;
    background: #fff;
    border-bottom: 1px solid #e4e7ed;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
  }

  .nav-brand a {
    font-size: 18px;
    font-weight: 600;
    color: #303133;
    text-decoration: none;
  }

  .nav-links {
    display: flex;
    gap: 24px;
    align-items: center;
  }

  .nav-links a {
    color: #606266;
    text-decoration: none;
    font-size: 14px;
    transition: color 0.2s;
  }

  .nav-links a:hover {
    color: #409eff;
  }

  .nav-user {
    display: flex;
    align-items: center;
    gap: 12px;
    position: relative;
  }

  .nav-user span {
    font-size: 14px;
    color: #606266;
  }

  .unread-badge {
    position: absolute;
    top: -8px;
    left: -8px;
    background: #f56c6c;
    color: #fff;
    font-size: 12px;
    padding: 2px 6px;
    border-radius: 10px;
    min-width: 18px;
    text-align: center;
  }

  .btn-logout {
    padding: 6px 12px;
    font-size: 13px;
    background: #f5f7fa;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    cursor: pointer;
    color: #606266;
    transition: all 0.2s;
  }

  .btn-logout:hover {
    background: #ecf5ff;
    border-color: #b3d8ff;
    color: #409eff;
  }

  .main-content {
    max-width: 1200px;
    margin: 0 auto;
    padding: 24px;
  }
</style>
