<script lang="ts">
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';

  $: user = $page.data.user;
</script>

{#if user}
  <div class="home">
    <div class="hero">
      <h1>欢迎回来，{user.name} 👋</h1>
      <p>高效协作，轻松处理每一个工单</p>
      <div class="hero-actions">
        <button class="btn-primary" on:click={() => goto('/tickets/new')}>
          + 新建工单
        </button>
        <button class="btn-secondary" on:click={() => goto('/tickets')}>
          查看所有工单
        </button>
      </div>
    </div>

    <div class="features">
      <div class="feature-card">
        <div class="feature-icon">📋</div>
        <h3>工单管理</h3>
        <p>完整的工单生命周期管理，从创建到完成全流程追踪</p>
      </div>
      <div class="feature-card">
        <div class="feature-icon">🔄</div>
        <h3>状态流转</h3>
        <p>待接单 → 处理中 → 审核中 → 已完成，清晰的状态流转</p>
      </div>
      <div class="feature-card">
        <div class="feature-icon">📢</div>
        <h3>实时通知</h3>
        <p>基于 SSE 的实时推送，工单变更即时获取</p>
      </div>
      <div class="feature-card">
        <div class="feature-icon">👥</div>
        <h3>团队协作</h3>
        <p>@提及同事，附件上传，操作日志，团队协作更高效</p>
      </div>
    </div>
  </div>
{:else}
  <div class="home">
    <div class="hero">
      <h1>📋 工单协同系统</h1>
      <p>实时协作，高效处理</p>
      <div class="hero-actions">
        <button class="btn-primary" on:click={() => goto('/login')}>
          立即登录
        </button>
      </div>
    </div>

    <div class="features">
      <div class="feature-card">
        <div class="feature-icon">📋</div>
        <h3>工单管理</h3>
        <p>完整的工单生命周期管理</p>
      </div>
      <div class="feature-card">
        <div class="feature-icon">🔄</div>
        <h3>状态流转</h3>
        <p>清晰的工单状态流转机制</p>
      </div>
      <div class="feature-card">
        <div class="feature-icon">📢</div>
        <h3>实时通知</h3>
        <p>SSE 实时推送，即时获取</p>
      </div>
      <div class="feature-card">
        <div class="feature-icon">👥</div>
        <h3>团队协作</h3>
        <p>@提及、附件、操作日志</p>
      </div>
    </div>
  </div>
{/if}

<style>
  .home {
    padding: 40px 0;
  }

  .hero {
    text-align: center;
    padding: 60px 20px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 16px;
    color: #fff;
    margin-bottom: 40px;
  }

  .hero h1 {
    font-size: 36px;
    margin: 0 0 16px 0;
  }

  .hero p {
    font-size: 18px;
    margin: 0 0 32px 0;
    opacity: 0.9;
  }

  .hero-actions {
    display: flex;
    gap: 16px;
    justify-content: center;
  }

  .btn-primary {
    padding: 12px 32px;
    background: #fff;
    color: #667eea;
    border: none;
    border-radius: 8px;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    transition: transform 0.2s;
  }

  .btn-primary:hover {
    transform: translateY(-2px);
  }

  .btn-secondary {
    padding: 12px 32px;
    background: transparent;
    color: #fff;
    border: 2px solid rgba(255, 255, 255, 0.5);
    border-radius: 8px;
    font-size: 16px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-secondary:hover {
    background: rgba(255, 255, 255, 0.1);
    border-color: #fff;
  }

  .features {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 24px;
  }

  .feature-card {
    background: #fff;
    padding: 32px;
    border-radius: 12px;
    text-align: center;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
    transition: transform 0.2s, box-shadow 0.2s;
  }

  .feature-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  }

  .feature-icon {
    font-size: 48px;
    margin-bottom: 16px;
  }

  .feature-card h3 {
    margin: 0 0 8px 0;
    color: #303133;
    font-size: 18px;
  }

  .feature-card p {
    margin: 0;
    color: #909399;
    font-size: 14px;
    line-height: 1.6;
  }
</style>
