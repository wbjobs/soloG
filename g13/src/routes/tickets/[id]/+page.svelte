<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { PUBLIC_POCKETBASE_URL } from '$env/static/public';
  import ChunkedUploader from '$lib/components/ChunkedUploader.svelte';
  import type {
    TicketsResponse,
    CommentsResponse,
    AttachmentsResponse,
    ActivityLogsResponse,
    UsersRecord,
    TimeLogsResponse
  } from '$lib/types/pocketbase';

  let ticketId: string;
  let ticket: TicketsResponse | null = null;
  let comments: CommentsResponse[] = [];
  let attachments: AttachmentsResponse[] = [];
  let activityLogs: ActivityLogsResponse[] = [];
  let timeLogs: TimeLogsResponse[] = [];
  let users: UsersRecord[] = [];
  let loading = true;
  let activeTab = 'comments';

  let timeLogHours = 1;
  let timeLogDescription = '';
  let timeLogDate = new Date().toISOString().split('T')[0];
  let timeLogLoading = false;

  let newComment = '';
  let mentionSearch = '';
  let showMentionList = false;
  let filteredUsers: UsersRecord[] = [];
  let selectedMentions: UsersRecord[] = [];

  let uploadLoading = false;
  let statusLoading = false;
  let assigneeLoading = false;

  $: ticketId = $page.params.id;

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

  const actionLabels: Record<string, string> = {
    create_ticket: '创建工单',
    change_status: '变更状态',
    assign_ticket: '分配工单',
    add_comment: '添加评论',
    upload_attachment: '上传附件',
    add_watcher: '添加关注者',
    add_time_log: '添加工时'
  };

  const slaPriorityConfig: Record<string, { escalationHours: number; label: string }> = {
    low: { escalationHours: 48, label: '低优先级' },
    medium: { escalationHours: 12, label: '中优先级' },
    high: { escalationHours: 4, label: '高优先级' }
  };

  const getSlaInfo = () => {
    if (!ticket || !ticket.sla_deadline) {
      return { status: 'normal', remainingText: '未设置', statusClass: '' };
    }

    const now = new Date();
    const deadline = new Date(ticket.sla_deadline);
    const remainingMs = deadline.getTime() - now.getTime();
    const remainingMinutes = Math.floor(remainingMs / (1000 * 60));

    if (ticket.status === 'completed') {
      return { status: 'completed', remainingText: '已完成', statusClass: 'sla-completed' };
    }

    if (remainingMinutes <= 0) {
      return {
        status: 'overdue',
        remainingText: `已超时 ${Math.abs(remainingMinutes)} 分钟`,
        statusClass: 'sla-overdue'
      };
    }

    const config = slaPriorityConfig[ticket.priority];
    const warningThreshold = config.escalationHours * 0.25 * 60;

    if (remainingMinutes <= warningThreshold) {
      const hours = Math.floor(remainingMinutes / 60);
      const mins = remainingMinutes % 60;
      return {
        status: 'warning',
        remainingText: `${hours}小时${mins}分钟`,
        statusClass: 'sla-warning'
      };
    }

    const hours = Math.floor(remainingMinutes / 60);
    const mins = remainingMinutes % 60;
    return {
      status: 'normal',
      remainingText: `${hours}小时${mins}分钟`,
      statusClass: 'sla-normal'
    };
  };

  const loadTicket = async () => {
    loading = true;
    try {
      const ticketRes = await fetch(`${PUBLIC_POCKETBASE_URL}/api/collections/tickets/records/${ticketId}?expand=creator,assignee,watchers`, { credentials: 'include' });
      if (ticketRes.ok) {
        ticket = await ticketRes.json();
      }

      const [commentsRes, attachmentsRes, activityRes, usersRes, timeLogsRes] = await Promise.all([
        fetch(`/api/tickets/${ticketId}/comments`, { credentials: 'include' }),
        fetch(`/api/tickets/${ticketId}/attachments`, { credentials: 'include' }),
        fetch(`/api/tickets/${ticketId}/activity`, { credentials: 'include' }),
        fetch('/api/users', { credentials: 'include' }),
        fetch(`/api/tickets/${ticketId}/time-logs`, { credentials: 'include' })
      ]);

      if (commentsRes.ok) comments = await commentsRes.json();
      if (attachmentsRes.ok) attachments = await attachmentsRes.json();
      if (activityRes.ok) activityLogs = await activityRes.json();
      if (usersRes.ok) users = await usersRes.json();
      if (timeLogsRes.ok) timeLogs = await timeLogsRes.json();
    } catch (e) {
      console.error('Failed to load ticket:', e);
    } finally {
      loading = false;
    }
  };

  const submitTimeLog = async () => {
    if (timeLogLoading || !timeLogHours || timeLogHours <= 0) return;

    timeLogLoading = true;
    try {
      const res = await fetch(`/api/tickets/${ticketId}/time-logs`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          hours: timeLogHours,
          description: timeLogDescription,
          log_date: timeLogDate
        })
      });

      if (res.ok) {
        timeLogHours = 1;
        timeLogDescription = '';
        loadTicket();
      }
    } catch (e) {
      console.error('Failed to submit time log:', e);
    } finally {
      timeLogLoading = false;
    }
  };

  onMount(() => {
    loadTicket();
  });

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('zh-CN');
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const changeStatus = async (status: 'pending' | 'processing' | 'reviewing' | 'completed') => {
    if (statusLoading) return;
    statusLoading = true;
    try {
      const res = await fetch(`/api/tickets/${ticketId}/status`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
      });
      if (res.ok) {
        loadTicket();
      }
    } finally {
      statusLoading = false;
    }
  };

  const changeAssignee = async (e: Event) => {
    const target = e.target as HTMLSelectElement;
    const assignee = target.value;
    if (!assignee || assigneeLoading) return;

    assigneeLoading = true;
    try {
      const res = await fetch(`/api/tickets/${ticketId}/assignee`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ assignee })
      });
      if (res.ok) {
        loadTicket();
      }
    } finally {
      assigneeLoading = false;
    }
  };

  const handleCommentInput = (e: Event) => {
    const target = e.target as HTMLTextAreaElement;
    newComment = target.value;

    const atIndex = newComment.lastIndexOf('@');
    if (atIndex !== -1 && atIndex === newComment.length - 1) {
      showMentionList = true;
      mentionSearch = '';
      filteredUsers = users.filter(u => u.id !== $page.data.user?.id);
    } else if (atIndex !== -1) {
      const searchStr = newComment.slice(atIndex + 1).toLowerCase();
      if (searchStr && !searchStr.includes(' ')) {
        mentionSearch = searchStr;
        showMentionList = true;
        filteredUsers = users.filter(u =>
          u.id !== $page.data.user?.id &&
          (u.name.toLowerCase().includes(searchStr) || u.email.toLowerCase().includes(searchStr))
        );
      } else {
        showMentionList = false;
      }
    } else {
      showMentionList = false;
    }
  };

  const selectMention = (user: UsersRecord) => {
    const atIndex = newComment.lastIndexOf('@');
    if (atIndex !== -1) {
      newComment = newComment.slice(0, atIndex) + `@${user.name} `;
      if (!selectedMentions.find(m => m.id === user.id)) {
        selectedMentions.push(user);
      }
    }
    showMentionList = false;
  };

  const submitComment = async () => {
    if (!newComment.trim()) return;

    try {
      const res = await fetch(`/api/tickets/${ticketId}/comments`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: newComment,
          mentions: selectedMentions.map(m => m.id)
        })
      });

      if (res.ok) {
        newComment = '';
        selectedMentions = [];
        loadTicket();
      }
    } catch (e) {
      console.error('Failed to submit comment:', e);
    }
  };

  let uploadError = '';

  const handleUploadSuccess = (e: { detail: { attachment: unknown } }) => {
    uploadError = '';
    loadTicket();
  };

  const handleUploadError = (e: { detail: { message: string } }) => {
    uploadError = e.detail.message;
    setTimeout(() => {
      uploadError = '';
    }, 5000);
  };

  const downloadAttachment = (attachment: AttachmentsResponse) => {
    const url = `${PUBLIC_POCKETBASE_URL}/api/collections/attachments/records/${attachment.id}/${attachment.file}`;
    window.open(url, '_blank');
  };

  const renderContentWithMentions = (content: string, mentions?: UsersRecord[]) => {
    if (!mentions || mentions.length === 0) return content;

    let result = content;
    for (const user of mentions) {
      const mentionPattern = new RegExp(`@${user.name}`, 'g');
      result = result.replace(mentionPattern, `<span class="mention">@${user.name}</span>`);
    }
    return result;
  };

  $: if (ticket && $page.data.user) {
    // Auto refresh when ticket data changes
  }
</script>

{#if !$page.data.user}
  <div class="no-auth">
    <p>请先登录</p>
    <button on:click={() => goto('/login')}>去登录</button>
  </div>
{:else if loading}
  <div class="loading">加载中...</div>
{:else if !ticket}
  <div class="empty">工单不存在</div>
{:else}
  <div class="ticket-detail">
    <div class="detail-header">
      <div>
        <button class="btn-back" on:click={() => goto('/tickets')}>← 返回列表</button>
      </div>
      <div class="header-actions">
        <span class={`priority ${priorityLabels[ticket.priority]?.class}`}>
          {priorityLabels[ticket.priority]?.label}优先级
        </span>
        <span class={`status ${statusLabels[ticket.status]?.class}`}>
          {statusLabels[ticket.status]?.label}
        </span>
      </div>
    </div>

    <div class="detail-content">
      <div class="main-content">
        <h1 class="ticket-title">{ticket.title}</h1>

        <div class="ticket-info">
          <div class="info-item">
            <span class="info-label">创建人：</span>
            <span class="info-value">{ticket.expand?.creator?.name || '-'}</span>
          </div>
          <div class="info-item">
            <span class="info-label">创建时间：</span>
            <span class="info-value">{formatDate(ticket.created)}</span>
          </div>
          <div class="info-item">
            <span class="info-label">更新时间：</span>
            <span class="info-value">{formatDate(ticket.updated)}</span>
          </div>
          <div class="info-item">
            <span class="info-label">处理人：</span>
            <select
              value={ticket.assignee || ''}
              on:change={changeAssignee}
              disabled={assigneeLoading}
              class="assignee-select"
            >
              <option value="">未分配</option>
              {#each users as user (user.id)}
                <option value={user.id}>{user.name}</option>
              {/each}
            </select>
          </div>
          <div class="info-item">
            <span class="info-label">SLA 状态：</span>
            <span class={`sla-badge ${getSlaInfo().statusClass}`}>
              {getSlaInfo().remainingText}
            </span>
          </div>
          <div class="info-item">
            <span class="info-label">累计工时：</span>
            <span class="info-value">{ticket.total_hours?.toFixed(1) || '0.0'} 小时</span>
          </div>
          {#if ticket.escalation_level && ticket.escalation_level > 0}
            <div class="info-item">
              <span class="info-label">升级等级：</span>
              <span class="escalation-badge">L{ticket.escalation_level}</span>
            </div>
          {/if}
        </div>

        <div class="ticket-description">
          <h3>工单描述</h3>
          <p>{ticket.description || '暂无描述'}</p>
        </div>

        <div class="status-actions">
          <h3>状态流转</h3>
          <div class="status-buttons">
            <button
              class={ticket.status === 'pending' ? 'active pending' : 'pending'}
              on:click={() => changeStatus('pending')}
              disabled={statusLoading || ticket.status === 'pending'}
            >
              待接单
            </button>
            <button
              class={ticket.status === 'processing' ? 'active processing' : 'processing'}
              on:click={() => changeStatus('processing')}
              disabled={statusLoading || ticket.status === 'processing'}
            >
              处理中
            </button>
            <button
              class={ticket.status === 'reviewing' ? 'active reviewing' : 'reviewing'}
              on:click={() => changeStatus('reviewing')}
              disabled={statusLoading || ticket.status === 'reviewing'}
            >
              审核中
            </button>
            <button
              class={ticket.status === 'completed' ? 'active completed' : 'completed'}
              on:click={() => changeStatus('completed')}
              disabled={statusLoading || ticket.status === 'completed'}
            >
              已完成
            </button>
          </div>
        </div>

        <div class="tabs">
          <button
            class={activeTab === 'comments' ? 'active' : ''}
            on:click={() => activeTab = 'comments'}
          >
            评论 ({comments.length})
          </button>
          <button
            class={activeTab === 'attachments' ? 'active' : ''}
            on:click={() => activeTab = 'attachments'}
          >
            附件 ({attachments.length})
          </button>
          <button
            class={activeTab === 'timelogs' ? 'active' : ''}
            on:click={() => activeTab = 'timelogs'}
          >
            工时 ({timeLogs.length})
          </button>
          <button
            class={activeTab === 'activity' ? 'active' : ''}
            on:click={() => activeTab = 'activity'}
          >
            操作日志 ({activityLogs.length})
          </button>
        </div>

        <div class="tab-content">
          {#if activeTab === 'comments'}
            <div class="comments-section">
              <div class="comment-input-wrapper">
                <textarea
                  bind:value={newComment}
                  on:input={handleCommentInput}
                  placeholder="输入评论，输入 @ 可以提及同事..."
                  rows={4}
                />
                {#if showMentionList && filteredUsers.length > 0}
                  <div class="mention-list">
                    {#each filteredUsers as user (user.id)}
                      <div class="mention-item" on:click={() => selectMention(user)}>
                        <span class="mention-name">{user.name}</span>
                        <span class="mention-email">{user.email}</span>
                      </div>
                    {/each}
                  </div>
                {/if}
                <div class="comment-actions">
                  <span class="mentions-preview">
                    {#each selectedMentions as m (m.id)}
                      <span class="mention-tag">@{m.name}</span>
                    {/each}
                  </span>
                  <button class="btn-primary" on:click={submitComment} disabled={!newComment.trim()}>
                    发表评论
                  </button>
                </div>
              </div>

              <div class="comments-list">
                {#if comments.length === 0}
                  <div class="empty-small">暂无评论</div>
                {:else}
                  {#each comments as comment (comment.id)}
                    <div class="comment-item">
                      <div class="comment-avatar">
                        {comment.expand?.author?.name?.[0] || 'U'}
                      </div>
                      <div class="comment-body">
                        <div class="comment-header">
                          <span class="comment-author">{comment.expand?.author?.name || '未知用户'}</span>
                          <span class="comment-time">{formatDate(comment.created)}</span>
                        </div>
                        <div class="comment-content">
                          {@html renderContentWithMentions(comment.content, comment.expand?.mentions)}
                        </div>
                      </div>
                    </div>
                  {/each}
                {/if}
              </div>
            </div>
          {:else if activeTab === 'attachments'}
            <div class="attachments-section">
              {#if uploadError}
                <div class="error-message">{uploadError}</div>
              {/if}

              <ChunkedUploader
                ticketId={ticketId}
                disabled={false}
                on:success={handleUploadSuccess}
                on:error={handleUploadError}
              />

              <div class="attachments-list">
                {#if attachments.length === 0}
                  <div class="empty-small">暂无附件</div>
                {:else}
                  {#each attachments as att (att.id)}
                    <div class="attachment-item" on:click={() => downloadAttachment(att)}>
                      <span class="file-icon">📄</span>
                      <div class="file-info">
                        <div class="file-name">{att.filename}</div>
                        <div class="file-meta">
                          {formatFileSize(att.size)} · {att.expand?.uploader?.name || '未知用户'} · {formatDate(att.created)}
                        </div>
                      </div>
                      <span class="download-icon">⬇️</span>
                    </div>
                  {/each}
                {/if}
              </div>
            </div>
          {:else if activeTab === 'timelogs'}
            <div class="timelogs-section">
              <div class="timelog-form">
                <h4>添加工时记录</h4>
                <div class="form-row">
                  <div class="form-group">
                    <label>日期：</label>
                    <input type="date" bind:value={timeLogDate} />
                  </div>
                  <div class="form-group">
                    <label>工时（小时）：</label>
                    <input
                      type="number"
                      bind:value={timeLogHours}
                      min="0.5"
                      step="0.5"
                      max="24"
                    />
                  </div>
                </div>
                <div class="form-group">
                  <label>工作描述：</label>
                  <textarea
                    bind:value={timeLogDescription}
                    placeholder="请描述完成的工作内容..."
                    rows={3}
                  />
                </div>
                <button
                  class="btn-primary"
                  on:click={submitTimeLog}
                  disabled={timeLogLoading || !timeLogHours || timeLogHours <= 0}
                >
                  {timeLogLoading ? '提交中...' : '提交工时'}
                </button>
              </div>

              <div class="timelogs-list">
                <h4>工时记录（共 {timeLogs.reduce((s, l) => s + l.hours, 0).toFixed(1)} 小时）</h4>
                {#if timeLogs.length === 0}
                  <div class="empty-small">暂无工时记录</div>
                {:else}
                  {#each timeLogs as log (log.id)}
                    <div class="timelog-item">
                      <div class="timelog-header">
                        <span class="timelog-date">{formatDate(log.log_date)}</span>
                        <span class="timelog-hours">{log.hours.toFixed(1)} 小时</span>
                      </div>
                      <div class="timelog-body">
                        <div class="timelog-user">
                          记录人：{(log as unknown as { expand?: { user?: { name: string } } }).expand?.user?.name || '未知用户'}
                        </div>
                        <div class="timelog-desc">{log.description || '无描述'}</div>
                      </div>
                    </div>
                  {/each}
                {/if}
              </div>
            </div>
          {:else if activeTab === 'activity'}
            <div class="activity-section">
              {#if activityLogs.length === 0}
                <div class="empty-small">暂无操作日志</div>
              {:else}
                <div class="activity-timeline">
                  {#each activityLogs as log (log.id)}
                    <div class="activity-item">
                      <div class="activity-dot"></div>
                      <div class="activity-content">
                        <div class="activity-header">
                          <span class="activity-action">{actionLabels[log.action] || log.action}</span>
                          <span class="activity-time">{formatDate(log.created)}</span>
                        </div>
                        <div class="activity-user">
                          操作人：{log.expand?.actor?.name || '未知用户'}
                        </div>
                        {#if log.old_value || log.new_value}
                          <div class="activity-details">
                            {#if log.old_value && log.new_value}
                              <span class="old-value">{statusLabels[log.old_value]?.label || log.old_value}</span>
                              <span class="arrow">→</span>
                              <span class="new-value">{statusLabels[log.new_value]?.label || log.new_value}</span>
                            {:else if log.new_value}
                              <span class="new-value">{log.new_value}</span>
                            {/if}
                          </div>
                        {/if}
                      </div>
                    </div>
                  {/each}
                </div>
              {/if}
            </div>
          {/if}
        </div>
      </div>

      <div class="sidebar">
        <div class="sidebar-card">
          <h3>关注者</h3>
          {#if ticket.expand?.watchers && ticket.expand.watchers.length > 0}
            <div class="watchers-list">
              {#each ticket.expand.watchers as watcher (watcher.id)}
                <div class="watcher-item">
                  <div class="watcher-avatar">{watcher.name?.[0] || 'U'}</div>
                  <span>{watcher.name}</span>
                </div>
              {/each}
            </div>
          {:else}
            <div class="empty-small">暂无关注者</div>
          {/if}
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  .ticket-detail {
    padding: 20px 0;
  }

  .detail-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
  }

  .btn-back {
    background: none;
    border: none;
    color: #606266;
    cursor: pointer;
    font-size: 14px;
    padding: 8px 12px;
    border-radius: 4px;
    transition: background 0.2s;
  }

  .btn-back:hover {
    background: #f5f7fa;
  }

  .header-actions {
    display: flex;
    gap: 12px;
  }

  .status, .priority {
    padding: 6px 16px;
    border-radius: 16px;
    font-size: 13px;
    font-weight: 500;
  }

  .status-pending, .pending {
    background: #fdf6ec;
    color: #e6a23c;
  }

  .status-processing, .processing {
    background: #ecf5ff;
    color: #409eff;
  }

  .status-reviewing, .reviewing {
    background: #f0f9eb;
    color: #67c23a;
  }

  .status-completed, .completed {
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

  .detail-content {
    display: grid;
    grid-template-columns: 1fr 300px;
    gap: 24px;
  }

  .main-content {
    background: #fff;
    border-radius: 8px;
    padding: 32px;
  }

  .ticket-title {
    margin: 0 0 24px 0;
    font-size: 24px;
    color: #303133;
  }

  .ticket-info {
    display: flex;
    flex-wrap: wrap;
    gap: 24px;
    padding: 16px;
    background: #f5f7fa;
    border-radius: 8px;
    margin-bottom: 24px;
  }

  .info-item {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .info-label {
    color: #909399;
    font-size: 13px;
  }

  .info-value {
    color: #606266;
    font-size: 13px;
  }

  .assignee-select {
    padding: 4px 8px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    font-size: 13px;
    background: #fff;
  }

  .ticket-description {
    margin-bottom: 24px;
  }

  .ticket-description h3 {
    margin: 0 0 12px 0;
    font-size: 16px;
    color: #303133;
  }

  .ticket-description p {
    margin: 0;
    color: #606266;
    line-height: 1.8;
    white-space: pre-wrap;
  }

  .status-actions {
    margin-bottom: 32px;
  }

  .status-actions h3 {
    margin: 0 0 16px 0;
    font-size: 16px;
    color: #303133;
  }

  .status-buttons {
    display: flex;
    gap: 12px;
  }

  .status-buttons button {
    flex: 1;
    padding: 12px;
    border: 2px solid transparent;
    border-radius: 8px;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s;
    font-weight: 500;
  }

  .status-buttons button:hover:not(:disabled):not(.active) {
    transform: translateY(-2px);
  }

  .status-buttons button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .status-buttons button.active {
    cursor: default;
    border-width: 2px;
  }

  .status-buttons .pending {
    background: #fdf6ec;
    color: #e6a23c;
    border-color: #f5dab1;
  }

  .status-buttons .pending.active {
    background: #e6a23c;
    color: #fff;
    border-color: #e6a23c;
  }

  .status-buttons .processing {
    background: #ecf5ff;
    color: #409eff;
    border-color: #b3d8ff;
  }

  .status-buttons .processing.active {
    background: #409eff;
    color: #fff;
    border-color: #409eff;
  }

  .status-buttons .reviewing {
    background: #f0f9eb;
    color: #67c23a;
    border-color: #c2e7b0;
  }

  .status-buttons .reviewing.active {
    background: #67c23a;
    color: #fff;
    border-color: #67c23a;
  }

  .status-buttons .completed {
    background: #f4f4f5;
    color: #909399;
    border-color: #d3d4d6;
  }

  .status-buttons .completed.active {
    background: #909399;
    color: #fff;
    border-color: #909399;
  }

  .tabs {
    display: flex;
    gap: 0;
    border-bottom: 2px solid #ebeef5;
    margin-bottom: 24px;
  }

  .tabs button {
    padding: 12px 24px;
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

  .comment-input-wrapper {
    position: relative;
    margin-bottom: 24px;
  }

  .comment-input-wrapper textarea {
    width: 100%;
    padding: 12px 16px;
    border: 1px solid #dcdfe6;
    border-radius: 8px;
    font-size: 14px;
    font-family: inherit;
    resize: vertical;
    min-height: 100px;
    box-sizing: border-box;
    transition: border-color 0.2s;
  }

  .comment-input-wrapper textarea:focus {
    outline: none;
    border-color: #409eff;
  }

  .mention-list {
    position: absolute;
    bottom: 60px;
    left: 0;
    background: #fff;
    border: 1px solid #e4e7ed;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    max-height: 200px;
    overflow-y: auto;
    z-index: 100;
    min-width: 200px;
  }

  .mention-item {
    padding: 10px 16px;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .mention-item:hover {
    background: #f5f7fa;
  }

  .mention-name {
    font-size: 14px;
    color: #303133;
  }

  .mention-email {
    font-size: 12px;
    color: #909399;
  }

  .comment-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 12px;
  }

  .mentions-preview {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .mention-tag {
    padding: 2px 8px;
    background: #ecf5ff;
    color: #409eff;
    border-radius: 4px;
    font-size: 12px;
  }

  .btn-primary {
    padding: 8px 20px;
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

  .comments-list {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .comment-item {
    display: flex;
    gap: 12px;
  }

  .comment-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: #409eff;
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    flex-shrink: 0;
  }

  .comment-body {
    flex: 1;
    background: #f5f7fa;
    padding: 16px;
    border-radius: 8px;
  }

  .comment-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }

  .comment-author {
    font-weight: 600;
    color: #303133;
    font-size: 14px;
  }

  .comment-time {
    color: #909399;
    font-size: 12px;
  }

  .comment-content {
    color: #606266;
    font-size: 14px;
    line-height: 1.6;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .comment-content :global(.mention) {
    color: #409eff;
    font-weight: 500;
  }

  .upload-area {
    margin-bottom: 24px;
  }

  .upload-label {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px;
    border: 2px dashed #dcdfe6;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
    color: #909399;
  }

  .upload-label:hover {
    border-color: #409eff;
    background: #ecf5ff;
    color: #409eff;
  }

  .upload-icon {
    font-size: 32px;
    margin-bottom: 8px;
  }

  .attachments-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .attachment-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    background: #f5f7fa;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .attachment-item:hover {
    background: #ecf5ff;
  }

  .file-icon, .download-icon {
    font-size: 24px;
  }

  .file-info {
    flex: 1;
  }

  .file-name {
    font-size: 14px;
    color: #303133;
    font-weight: 500;
  }

  .file-meta {
    font-size: 12px;
    color: #909399;
    margin-top: 2px;
  }

  .activity-timeline {
    position: relative;
    padding-left: 24px;
  }

  .activity-timeline::before {
    content: '';
    position: absolute;
    left: 8px;
    top: 0;
    bottom: 0;
    width: 2px;
    background: #ebeef5;
  }

  .activity-item {
    position: relative;
    padding-bottom: 24px;
  }

  .activity-dot {
    position: absolute;
    left: -20px;
    top: 4px;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #409eff;
    border: 2px solid #fff;
    box-shadow: 0 0 0 2px #409eff;
  }

  .activity-content {
    background: #f5f7fa;
    padding: 12px 16px;
    border-radius: 8px;
  }

  .activity-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
  }

  .activity-action {
    font-weight: 600;
    color: #303133;
    font-size: 14px;
  }

  .activity-time {
    color: #909399;
    font-size: 12px;
  }

  .activity-user {
    color: #606266;
    font-size: 13px;
    margin-bottom: 4px;
  }

  .activity-details {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 8px;
  }

  .old-value {
    padding: 2px 8px;
    background: #fef0f0;
    color: #f56c6c;
    border-radius: 4px;
    font-size: 12px;
  }

  .new-value {
    padding: 2px 8px;
    background: #f0f9eb;
    color: #67c23a;
    border-radius: 4px;
    font-size: 12px;
  }

  .arrow {
    color: #909399;
  }

  .sidebar {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .sidebar-card {
    background: #fff;
    border-radius: 8px;
    padding: 20px;
  }

  .sidebar-card h3 {
    margin: 0 0 16px 0;
    font-size: 16px;
    color: #303133;
  }

  .watchers-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .watcher-item {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .watcher-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: #67c23a;
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    font-weight: 600;
  }

  .loading, .empty, .no-auth {
    text-align: center;
    padding: 60px 20px;
    background: #fff;
    border-radius: 8px;
    color: #909399;
  }

  .empty-small {
    text-align: center;
    padding: 40px 20px;
    color: #909399;
    font-size: 14px;
  }

  .sla-badge {
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 500;
  }

  .sla-normal {
    background: #f0f9eb;
    color: #67c23a;
  }

  .sla-warning {
    background: #fdf6ec;
    color: #e6a23c;
  }

  .sla-overdue {
    background: #fef0f0;
    color: #f56c6c;
  }

  .sla-completed {
    background: #f4f4f5;
    color: #909399;
  }

  .escalation-badge {
    padding: 4px 10px;
    background: #fef0f0;
    color: #f56c6c;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
  }

  .timelogs-section {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .timelog-form {
    background: #f5f7fa;
    padding: 20px;
    border-radius: 8px;
  }

  .timelog-form h4 {
    margin: 0 0 16px 0;
    font-size: 16px;
    color: #303133;
  }

  .form-row {
    display: flex;
    gap: 24px;
    margin-bottom: 16px;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
    flex: 1;
  }

  .form-group label {
    font-size: 13px;
    color: #606266;
  }

  .form-group input,
  .form-group textarea {
    padding: 10px 12px;
    border: 1px solid #dcdfe6;
    border-radius: 6px;
    font-size: 14px;
    font-family: inherit;
    resize: vertical;
  }

  .form-group input:focus,
  .form-group textarea:focus {
    outline: none;
    border-color: #409eff;
  }

  .timelogs-list h4 {
    margin: 0 0 16px 0;
    font-size: 16px;
    color: #303133;
  }

  .timelog-item {
    background: #fff;
    padding: 16px;
    border-radius: 8px;
    border: 1px solid #ebeef5;
    margin-bottom: 12px;
  }

  .timelog-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }

  .timelog-date {
    font-size: 13px;
    color: #909399;
  }

  .timelog-hours {
    font-size: 14px;
    font-weight: 600;
    color: #409eff;
  }

  .timelog-body {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .timelog-user {
    font-size: 13px;
    color: #606266;
  }

  .timelog-desc {
    font-size: 14px;
    color: #303133;
    line-height: 1.5;
  }
</style>
