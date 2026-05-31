<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import type { TicketsResponse } from '$lib/types/pocketbase';

  let tickets: TicketsResponse[] = [];
  let loading = true;
  let draggedTicket: TicketsResponse | null = null;
  let dragOverColumn: string | null = null;

  const columns: Array<{ id: 'pending' | 'processing' | 'reviewing' | 'completed'; label: string; color: string }> = [
    { id: 'pending', label: '待接单', color: '#e6a23c' },
    { id: 'processing', label: '处理中', color: '#409eff' },
    { id: 'reviewing', label: '审核中', color: '#67c23a' },
    { id: 'completed', label: '已完成', color: '#909399' }
  ];

  const priorityLabels: Record<string, { label: string; class: string }> = {
    low: { label: '低', class: 'priority-low' },
    medium: { label: '中', class: 'priority-medium' },
    high: { label: '高', class: 'priority-high' }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('zh-CN');
  };

  const getTicketsByStatus = (status: string) => {
    return tickets.filter((t) => t.status === status);
  };

  const loadTickets = async () => {
    loading = true;
    try {
      const res = await fetch('/api/tickets?perPage=100', { credentials: 'include' });
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

  const onDragStart = (ticket: TicketsResponse) => {
    draggedTicket = ticket;
  };

  const onDragOver = (e: DragEvent, status: string) => {
    e.preventDefault();
    dragOverColumn = status;
  };

  const onDragLeave = () => {
    dragOverColumn = null;
  };

  const onDrop = async (e: DragEvent, status: string) => {
    e.preventDefault();
    dragOverColumn = null;

    if (!draggedTicket || draggedTicket.status === status) {
      draggedTicket = null;
      return;
    }

    const ticketId = draggedTicket.id;
    const oldStatus = draggedTicket.status;
    draggedTicket = null;

    try {
      const res = await fetch(`/api/tickets/${ticketId}/status`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
      });

      if (res.ok) {
        loadTickets();
      }
    } catch (err) {
      console.error('Failed to update ticket status:', err);
    }
  };

  const onDragEnd = () => {
    draggedTicket = null;
    dragOverColumn = null;
  };
</script>

{#if !$page.data.user}
  <div class="no-auth">
    <p>请先登录</p>
    <button on:click={() => goto('/login')}>去登录</button>
  </div>
{:else}
  <div class="kanban-page">
    <div class="page-header">
      <h1>看板视图</h1>
      <div class="header-actions">
        <button class="btn-secondary" on:click={loadTickets}>
          🔄 刷新
        </button>
        <button class="btn-primary" on:click={() => goto('/tickets')}>
          📋 列表视图
        </button>
      </div>
    </div>

    {#if loading}
      <div class="loading">加载中...</div>
    {:else}
      <div class="kanban-board">
        {#each columns as column (column.id)}
          <div
            class="kanban-column"
            class:drag-over={dragOverColumn === column.id}
            on:dragover={(e) => onDragOver(e, column.id)}
            on:dragleave={onDragLeave}
            on:drop={(e) => onDrop(e, column.id)}
          >
            <div class="column-header" style="border-left-color: {column.color}">
              <h3>{column.label}</h3>
              <span class="ticket-count">{getTicketsByStatus(column.id).length}</span>
            </div>

            <div class="column-content">
              {#each getTicketsByStatus(column.id) as ticket (ticket.id)}
                <div
                  class="kanban-card"
                  draggable="true"
                  on:dragstart={() => onDragStart(ticket)}
                  on:dragend={onDragEnd}
                  on:click={() => goto(`/tickets/${ticket.id}`)}
                  class:dragging={draggedTicket?.id === ticket.id}
                >
                  <div class="card-header">
                    <span class={`priority ${priorityLabels[ticket.priority]?.class}`}>
                      {priorityLabels[ticket.priority]?.label}
                    </span>
                  </div>
                  <h4 class="card-title">{ticket.title}</h4>
                  <p class="card-desc">
                    {ticket.description.slice(0, 60)}{ticket.description.length > 60 ? '...' : ''}
                  </p>
                  <div class="card-footer">
                    <div class="card-assignee">
                      {#if ticket.expand?.assignee}
                        <span class="assignee-avatar">
                          {ticket.expand.assignee.name?.[0] || 'U'}
                        </span>
                        <span>{ticket.expand.assignee.name}</span>
                      {:else}
                        <span class="no-assignee">未分配</span>
                      {/if}
                    </div>
                    <span class="card-date">{formatDate(ticket.created)}</span>
                  </div>
                </div>
              {/each}

              {#if getTicketsByStatus(column.id).length === 0}
                <div class="empty-column">
                  <span>暂无工单</span>
                </div>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>
{/if}

<style>
  .kanban-page {
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

  .header-actions {
    display: flex;
    gap: 12px;
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

  .btn-secondary {
    padding: 10px 20px;
    background: #fff;
    color: #606266;
    border: 1px solid #dcdfe6;
    border-radius: 6px;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-secondary:hover {
    background: #f5f7fa;
  }

  .loading, .no-auth {
    text-align: center;
    padding: 60px 20px;
    background: #fff;
    border-radius: 8px;
    color: #909399;
  }

  .kanban-board {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    min-height: 600px;
  }

  .kanban-column {
    background: #f5f7fa;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    min-height: 500px;
    transition: all 0.2s;
  }

  .kanban-column.drag-over {
    background: #ecf5ff;
    box-shadow: 0 0 0 2px #409eff;
  }

  .column-header {
    padding: 16px;
    background: #fff;
    border-radius: 8px 8px 0 0;
    border-left: 4px solid;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .column-header h3 {
    margin: 0;
    font-size: 16px;
    color: #303133;
  }

  .ticket-count {
    background: #e4e7ed;
    color: #606266;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 12px;
    min-width: 24px;
    text-align: center;
  }

  .column-content {
    padding: 12px;
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .kanban-card {
    background: #fff;
    padding: 16px;
    border-radius: 8px;
    cursor: grab;
    transition: all 0.2s;
    border: 1px solid #e4e7ed;
  }

  .kanban-card:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    transform: translateY(-2px);
  }

  .kanban-card.dragging {
    opacity: 0.5;
  }

  .kanban-card:active {
    cursor: grabbing;
  }

  .card-header {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 8px;
  }

  .priority {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 500;
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

  .card-title {
    margin: 0 0 8px 0;
    font-size: 14px;
    color: #303133;
    line-height: 1.4;
  }

  .card-desc {
    margin: 0 0 12px 0;
    font-size: 12px;
    color: #606266;
    line-height: 1.5;
  }

  .card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 12px;
    border-top: 1px solid #ebeef5;
  }

  .card-assignee {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: #606266;
  }

  .assignee-avatar {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: #409eff;
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    font-weight: 600;
  }

  .no-assignee {
    color: #c0c4cc;
    font-size: 12px;
  }

  .card-date {
    font-size: 11px;
    color: #c0c4cc;
  }

  .empty-column {
    text-align: center;
    padding: 40px 20px;
    color: #c0c4cc;
    font-size: 13px;
  }
</style>
