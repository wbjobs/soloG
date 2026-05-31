<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import type { TimeLogsResponse } from '$lib/types/pocketbase';

  let startDate = '';
  let endDate = '';
  let loading = false;
  let report: {
    totalHours: number;
    ticketCount: number;
    byUser: Array<{ userId: string; userName: string; hours: number; ticketCount: number }>;
    byTicket: Array<{ ticketId: string; ticketTitle: string; hours: number; userCount: number }>;
    logs: TimeLogsResponse[];
  } | null = null;

  let activeTab = 'summary';

  const formatHours = (hours: number): string => {
    return hours.toFixed(1) + ' 小时';
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('zh-CN');
  };

  onMount(() => {
    const today = new Date();
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);

    startDate = firstDay.toISOString().split('T')[0];
    endDate = today.toISOString().split('T')[0];
  });

  const generateReport = async () => {
    if (!startDate || !endDate) return;

    loading = true;
    try {
      const params = new URLSearchParams({
        startDate: startDate + 'T00:00:00.000Z',
        endDate: endDate + 'T23:59:59.999Z'
      });

      const res = await fetch(`/api/reports/time?${params.toString()}`, {
        credentials: 'include'
      });

      if (res.ok) {
        report = await res.json();
      }
    } catch (e) {
      console.error('Failed to generate report:', e);
    } finally {
      loading = false;
    }
  };

  $: startDate, endDate, generateReport();
</script>

{#if !$page.data.user}
  <div class="no-auth">
    <p>请先登录</p>
    <button on:click={() => goto('/login')}>去登录</button>
  </div>
{:else}
  <div class="reports-page">
    <div class="page-header">
      <h1>工时统计报表</h1>
    </div>

    <div class="filter-bar">
      <div class="filter-group">
        <label>开始日期：</label>
        <input type="date" bind:value={startDate} max={endDate} />
      </div>
      <div class="filter-group">
        <label>结束日期：</label>
        <input type="date" bind:value={endDate} min={startDate} />
      </div>
      <button class="btn-primary" on:click={generateReport} disabled={loading}>
        {loading ? '生成中...' : '生成报表'}
      </button>
    </div>

    {#if loading}
      <div class="loading">加载中...</div>
    {:else if !report}
      <div class="empty">选择日期范围生成报表</div>
    {:else}
      <div class="report-content">
        <div class="summary-cards">
          <div class="summary-card">
            <div class="card-icon">⏱️</div>
            <div class="card-info">
              <div class="card-value">{formatHours(report.totalHours)}</div>
              <div class="card-label">总工时</div>
            </div>
          </div>
          <div class="summary-card">
            <div class="card-icon">📋</div>
            <div class="card-info">
              <div class="card-value">{report.ticketCount}</div>
              <div class="card-label">工单数量</div>
            </div>
          </div>
          <div class="summary-card">
            <div class="card-icon">👥</div>
            <div class="card-info">
              <div class="card-value">{report.byUser.length}</div>
              <div class="card-label">参与人员</div>
            </div>
          </div>
          <div class="summary-card">
            <div class="card-icon">📊</div>
            <div class="card-info">
              <div class="card-value">{report.logs.length}</div>
              <div class="card-label">记录条数</div>
            </div>
          </div>
        </div>

        <div class="tabs">
          <button
            class={activeTab === 'summary' ? 'active' : ''}
            on:click={() => activeTab = 'summary'}
          >
            按人员统计
          </button>
          <button
            class={activeTab === 'tickets' ? 'active' : ''}
            on:click={() => activeTab = 'tickets'}
          >
            按工单统计
          </button>
          <button
            class={activeTab === 'details' ? 'active' : ''}
            on:click={() => activeTab = 'details'}
          >
            详细记录
          </button>
        </div>

        <div class="tab-content">
          {#if activeTab === 'summary'}
            <div class="table-container">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>人员</th>
                    <th>工单数量</th>
                    <th>总工时</th>
                    <th>平均工单工时</th>
                  </tr>
                </thead>
                <tbody>
                  {#each report.byUser as user (user.userId)}
                    <tr>
                      <td>{user.userName}</td>
                      <td>{user.ticketCount}</td>
                      <td>{formatHours(user.hours)}</td>
                      <td>{formatHours(user.ticketCount > 0 ? user.hours / user.ticketCount : 0)}</td>
                    </tr>
                  {/each}
                  {#if report.byUser.length === 0}
                    <tr>
                      <td colspan="4" class="empty-cell">暂无数据</td>
                    </tr>
                  {/if}
                </tbody>
              </table>
            </div>
          {:else if activeTab === 'tickets'}
            <div class="table-container">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>工单</th>
                    <th>参与人数</th>
                    <th>总工时</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {#each report.byTicket as ticket (ticket.ticketId)}
                    <tr>
                      <td>{ticket.ticketTitle}</td>
                      <td>{ticket.userCount}</td>
                      <td>{formatHours(ticket.hours)}</td>
                      <td>
                        <button
                          class="link-btn"
                          on:click={() => goto(`/tickets/${ticket.ticketId}`)}
                        >
                          查看详情
                        </button>
                      </td>
                    </tr>
                  {/each}
                  {#if report.byTicket.length === 0}
                    <tr>
                      <td colspan="4" class="empty-cell">暂无数据</td>
                    </tr>
                  {/if}
                </tbody>
              </table>
            </div>
          {:else if activeTab === 'details'}
            <div class="table-container">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>日期</th>
                    <th>人员</th>
                    <th>工单</th>
                    <th>工时</th>
                    <th>描述</th>
                  </tr>
                </thead>
                <tbody>
                  {#each report.logs as log (log.id)}
                    <tr>
                      <td>{formatDate(log.log_date)}</td>
                      <td>
                        {(log as unknown as { expand?: { user?: { name: string } } }).expand?.user?.name || '未知用户'}
                      </td>
                      <td>
                        {(log as unknown as { expand?: { ticket?: { title: string } } }).expand?.ticket?.title || '未知工单'}
                      </td>
                      <td>{formatHours(log.hours)}</td>
                      <td>{log.description || '-'}</td>
                    </tr>
                  {/each}
                  {#if report.logs.length === 0}
                    <tr>
                      <td colspan="5" class="empty-cell">暂无数据</td>
                    </tr>
                  {/if}
                </tbody>
              </table>
            </div>
          {/if}
        </div>
      </div>
    {/if}
  </div>
{/if}

<style>
  .reports-page {
    padding: 20px 0;
  }

  .page-header {
    margin-bottom: 24px;
  }

  .page-header h1 {
    margin: 0;
    font-size: 24px;
    color: #303133;
  }

  .filter-bar {
    display: flex;
    gap: 24px;
    align-items: center;
    padding: 20px;
    background: #fff;
    border-radius: 8px;
    margin-bottom: 24px;
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

  .filter-group input {
    padding: 8px 12px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    font-size: 14px;
  }

  .btn-primary {
    padding: 10px 24px;
    background: #409eff;
    color: #fff;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    cursor: pointer;
    transition: background 0.2s;
  }

  .btn-primary:hover:not(:disabled) {
    background: #66b1ff;
  }

  .btn-primary:disabled {
    background: #a0cfff;
    cursor: not-allowed;
  }

  .loading, .empty, .no-auth {
    text-align: center;
    padding: 60px 20px;
    background: #fff;
    border-radius: 8px;
    color: #909399;
  }

  .report-content {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .summary-cards {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
  }

  .summary-card {
    background: #fff;
    padding: 24px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    gap: 16px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  }

  .card-icon {
    font-size: 40px;
  }

  .card-info {
    flex: 1;
  }

  .card-value {
    font-size: 24px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 4px;
  }

  .card-label {
    font-size: 13px;
    color: #909399;
  }

  .tabs {
    display: flex;
    gap: 0;
    background: #fff;
    border-radius: 8px;
    padding: 0 16px;
    border-bottom: 2px solid #ebeef5;
  }

  .tabs button {
    padding: 16px 24px;
    background: none;
    border: none;
    font-size: 14px;
    cursor: pointer;
    color: #606266;
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
    transition: all 0.2s;
  }

  .tabs button:hover {
    color: #409eff;
  }

  .tabs button.active {
    color: #409eff;
    border-bottom-color: #409eff;
    font-weight: 500;
  }

  .tab-content {
    background: #fff;
    border-radius: 8px;
    padding: 24px;
  }

  .table-container {
    overflow-x: auto;
  }

  .data-table {
    width: 100%;
    border-collapse: collapse;
  }

  .data-table th {
    background: #f5f7fa;
    padding: 12px 16px;
    text-align: left;
    font-size: 13px;
    font-weight: 600;
    color: #606266;
    border-bottom: 2px solid #ebeef5;
  }

  .data-table td {
    padding: 12px 16px;
    font-size: 14px;
    color: #606266;
    border-bottom: 1px solid #ebeef5;
  }

  .data-table tbody tr:hover {
    background: #f5f7fa;
  }

  .empty-cell {
    text-align: center;
    color: #c0c4cc;
    padding: 40px !important;
  }

  .link-btn {
    background: none;
    border: none;
    color: #409eff;
    cursor: pointer;
    font-size: 13px;
    padding: 0;
  }

  .link-btn:hover {
    text-decoration: underline;
  }
</style>
