<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import type { TicketsResponse } from '$lib/types/pocketbase';

  let tickets: TicketsResponse[] = [];
  let loading = true;
  let filterStatus = '';
  let filterAssignee = '';

  const statusLabels: Record<string, { label: string; class: string }> = {
    pending: { label: '待接单', class: 'status-pending' },
    processing: { label: '处理中', class: 'status-processing' },
    reviewing: { label: '审核中', class: 'status-reviewing' },
    completed: { label: '已完成', class: 'status-completed' }
  };

  const priorityLabels: Record<string, { label: string; class: string }> = {
    low: { label: '低', class: 'priority-low' },
    medium: { label: '中', class: 'priority-medium' },
    high: { label: '高', class: 'priority-high' }
  };

  const loadTickets = async () => {
    loading = true;
    try {
      const params = new URLSearchParams();
      if (filterStatus) params.set('status', filterStatus);
      if (filterAssignee) params.set('assignee', filterAssignee);

      const res = await fetch(`/api/tickets?${params.toString()}`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        tickets = data.items || [];
      }
    } finally {
      loading = false;
    }
  };

  onMount(() => {
    loadTickets();
  });

  $: filterStatus, filterAssignee, loadTickets();

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('zh-CN');
  };
</script>

{#if !$page.data.user}
  <div class="no-auth">
    <p>请先登录</p>
    <button on:click={() => goto('/login')}>去登录</button>
  </div>
{:else}
  <div class="tickets-page">
    <div class="page-header">
      <h1>工单列表</h1>
      <button class="btn-primary" on:click={() => goto('/tickets/new')}>
        + 新建工单
      </button>
    </div>

    <div class="filters">
      <div class="filter-group">
        <label>状态：</label>
        <select bind:value={filterStatus}>
          <option value="">全部</option>
          <option value="pending">待接单</option>
          <option value="processing">处理中</option>
          <option value="reviewing">审核中</option>
          <option value="completed">已完成</option>
        </select>
      </div>
    </div>

    {#if loading}
      <div class="loading">加载中...</div>
    {:else if tickets.length === 0}
      <div class="empty">
        <p>暂无工单</p>
        <button class="btn-primary" on:click={() => goto('/tickets/new')}>
          创建第一个工单
        </button>
      </div>
    {:else}
      <div class="tickets-grid">
        {#each tickets as ticket (ticket.id)}
          <div class="ticket-card" on:click={() => goto(`/tickets/${ticket.id}`)}>
            <div class="ticket-header">
              <span class={`priority ${priorityLabels[ticket.priority]?.class}`}>
                {priorityLabels[ticket.priority]?.label}
              </span>
              <span class={`status ${statusLabels[ticket.status]?.class}`}>
                {statusLabels[ticket.status]?.label}
              </span>
            </div>
            <h3 class="ticket-title">{ticket.title}</h3>
            <p class="ticket-desc">{ticket.description.slice(0, 100)}{ticket.description.length > 100 ? '...' : ''}</p>
            <div class="ticket-meta">
              <div class="meta-item">
                <span>创建人：</span>
                <span>{ticket.expand?.creator?.name || '-'}</span>
              </div>
              <div class="meta-item">
                <span>处理人：</span>
                <span>{ticket.expand?.assignee?.name || '未分配'}</span>
              </div>
              <div class="meta-item">
                <span>创建时间：</span>
                <span>{formatDate(ticket.created)}</span>
              </div>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>
{/if}

<style>
  .tickets-page {
    padding: 20px 0;
  }

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
  }

  .page-header h1 {
    margin: 0;
    font-size: 24px;
    color: #303133;
  }

  .btn-primary {
    padding: 10px 20px;
    background: #409eff;
    color: #fff;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    cursor: pointer;
    transition: background 0.2s;
  }

  .btn-primary:hover {
    background: #66b1ff;
  }

  .filters {
    display: flex;
    gap: 24px;
    margin-bottom: 24px;
    padding: 16px;
    background: #fff;
    border-radius: 8px;
  }

  .filter-group {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .filter-group label {
    font-size: 14px;
    color: #606266;
  }

  .filter-group select {
    padding: 6px 12px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    font-size: 14px;
    background: #fff;
  }

  .loading, .empty, .no-auth {
    text-align: center;
    padding: 60px 20px;
    background: #fff;
    border-radius: 8px;
    color: #909399;
  }

  .tickets-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 16px;
  }

  .ticket-card {
    background: #fff;
    padding: 20px;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
    border: 1px solid transparent;
  }

  .ticket-card:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    border-color: #409eff;
    transform: translateY(-2px);
  }

  .ticket-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 12px;
  }

  .status, .priority {
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 500;
  }

  .status-pending {
    background: #fdf6ec;
    color: #e6a23c;
  }

  .status-processing {
    background: #ecf5ff;
    color: #409eff;
  }

  .status-reviewing {
    background: #f0f9eb;
    color: #67c23a;
  }

  .status-completed {
    background: #f4f4f5;
    color: #909399;
  }

  .priority-low {
    background: #f4f4f5;
    color: #909399;
  }

  .priority-medium {
    background: #ecf5ff;
    color: #409eff;
  }

  .priority-high {
    background: #fef0f0;
    color: #f56c6c;
  }

  .ticket-title {
    margin: 0 0 8px 0;
    font-size: 16px;
    color: #303133;
    line-height: 1.4;
  }

  .ticket-desc {
    margin: 0 0 16px 0;
    font-size: 13px;
    color: #606266;
    line-height: 1.5;
  }

  .ticket-meta {
    border-top: 1px solid #ebeef5;
    padding-top: 12px;
  }

  .meta-item {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    color: #909399;
    margin-bottom: 4px;
  }

  .meta-item:last-child {
    margin-bottom: 0;
  }
</style>
