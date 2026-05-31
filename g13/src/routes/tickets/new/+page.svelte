<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import type { UsersRecord } from '$lib/types/pocketbase';

  let title = '';
  let description = '';
  let priority: 'low' | 'medium' | 'high' = 'medium';
  let assignee = '';
  let users: UsersRecord[] = [];
  let loading = false;
  let submitting = false;
  let error = '';

  onMount(async () => {
    try {
      const res = await fetch('/api/users', { credentials: 'include' });
      if (res.ok) {
        users = await res.json();
      }
    } catch (e) {
      console.error('Failed to load users:', e);
    } finally {
      loading = false;
    }
  });

  const handleSubmit = async (e: Event) => {
    e.preventDefault();
    if (!title.trim()) {
      error = '请输入工单标题';
      return;
    }

    submitting = true;
    error = '';

    try {
      const res = await fetch('/api/tickets', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: title.trim(),
          description: description.trim(),
          priority,
          assignee: assignee || undefined
        })
      });

      if (res.ok) {
        goto('/tickets');
      } else {
        error = '创建工单失败，请稍后重试';
      }
    } catch (e) {
      error = '网络错误，请稍后重试';
    } finally {
      submitting = false;
    }
  };
</script>

{#if !$page.data.user}
  <div class="no-auth">
    <p>请先登录</p>
    <button on:click={() => goto('/login')}>去登录</button>
  </div>
{:else}
  <div class="new-ticket-page">
    <div class="page-header">
      <h1>新建工单</h1>
      <button class="btn-secondary" on:click={() => goto('/tickets')}>
        返回列表
      </button>
    </div>

    <form on:submit={handleSubmit} class="ticket-form">
      <div class="form-group">
        <label for="title">工单标题 <span class="required">*</span></label>
        <input
          type="text"
          id="title"
          bind:value={title}
          placeholder="请输入工单标题"
          required
          disabled={submitting}
        />
      </div>

      <div class="form-row">
        <div class="form-group">
          <label for="priority">优先级</label>
          <select id="priority" bind:value={priority} disabled={submitting}>
            <option value="low">低</option>
            <option value="medium">中</option>
            <option value="high">高</option>
          </select>
        </div>

        <div class="form-group">
          <label for="assignee">指派给</label>
          <select id="assignee" bind:value={assignee} disabled={submitting || loading}>
            <option value="">未指派</option>
            {#each users as user (user.id)}
              <option value={user.id}>{user.name}</option>
            {/each}
          </select>
        </div>
      </div>

      <div class="form-group">
        <label for="description">工单描述</label>
        <textarea
          id="description"
          bind:value={description}
          placeholder="请详细描述工单内容..."
          rows={8}
          disabled={submitting}
        />
      </div>

      {#if error}
        <div class="error-message">{error}</div>
      {/if}

      <div class="form-actions">
        <button type="button" class="btn-secondary" on:click={() => goto('/tickets')} disabled={submitting}>
          取消
        </button>
        <button type="submit" class="btn-primary" disabled={submitting}>
          {submitting ? '创建中...' : '创建工单'}
        </button>
      </div>
    </form>
  </div>
{/if}

<style>
  .new-ticket-page {
    max-width: 800px;
    margin: 0 auto;
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

  .btn-secondary:hover:not(:disabled) {
    background: #ecf5ff;
    border-color: #b3d8ff;
    color: #409eff;
  }

  .btn-secondary:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .ticket-form {
    background: #fff;
    padding: 32px;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
  }

  label {
    font-size: 14px;
    color: #606266;
    font-weight: 500;
  }

  .required {
    color: #f56c6c;
  }

  input, select, textarea {
    padding: 10px 12px;
    border: 1px solid #dcdfe6;
    border-radius: 6px;
    font-size: 14px;
    font-family: inherit;
    transition: border-color 0.2s;
  }

  input:focus, select:focus, textarea:focus {
    outline: none;
    border-color: #409eff;
  }

  input:disabled, select:disabled, textarea:disabled {
    background: #f5f7fa;
    cursor: not-allowed;
  }

  textarea {
    resize: vertical;
    min-height: 120px;
  }

  .error-message {
    padding: 12px;
    background: #fef0f0;
    border: 1px solid #fbc4c4;
    border-radius: 6px;
    color: #f56c6c;
    font-size: 13px;
  }

  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
  }

  .no-auth {
    text-align: center;
    padding: 60px 20px;
    background: #fff;
    border-radius: 8px;
    color: #909399;
  }
</style>
