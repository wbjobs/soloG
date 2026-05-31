using ConfigCenter.Core.Interfaces;
using ConfigCenter.Infrastructure.Caching;
using ConfigCenter.Infrastructure.Data;
using ConfigCenter.Infrastructure.Services;
using ConfigCenter.Grpc.Services;
using ConfigCenter.Server.Components;
using Microsoft.EntityFrameworkCore;
using MudBlazor.Services;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddDbContext<ConfigCenterDbContext>(options =>
    options.UseSqlite(builder.Configuration.GetConnectionString("DefaultConnection")));

builder.Services.AddSingleton<IEncryptionService>(sp =>
    new AesEncryptionService(builder.Configuration["EncryptionKey"] ?? "ConfigCenter@AES256-SecretKey!2024"));
builder.Services.AddSingleton<IConfigChangeNotifier, InMemoryConfigChangeNotifier>();
builder.Services.AddSingleton<IConfigCache>(sp =>
    new LruConfigCache(int.Parse(builder.Configuration["Cache:Capacity"] ?? "1000")));
builder.Services.AddScoped<IConfigService, ConfigService>();
builder.Services.AddScoped<IImportExportService, ImportExportService>();
builder.Services.AddScoped<IAuditService, AuditService>();
builder.Services.AddScoped<IDependencyAnalyzer, DependencyAnalyzer>();

builder.Services.AddGrpc();
builder.Services.AddMudServices();

builder.Services.AddRazorComponents()
    .AddInteractiveServerComponents();

builder.Services.AddControllers();
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new Microsoft.OpenApi.Models.OpenApiInfo { Title = "ConfigCenter API", Version = "v1" });
});

var app = builder.Build();

using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<ConfigCenterDbContext>();
    db.Database.EnsureCreated();
}

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error", createScopeForErrors: true);
    app.UseHsts();
}

app.UseHttpsRedirection();
app.UseStaticFiles();
app.UseAntiforgery();

app.UseSwagger();
app.UseSwaggerUI(c =>
{
    c.SwaggerEndpoint("/swagger/v1/swagger.json", "ConfigCenter API v1");
});

app.MapGrpcService<ConfigCenterGrpcService>();
app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode();

app.MapControllers();

app.MapGet("/", () => "ConfigCenter Server is running. Visit /configs for Web UI.");

app.Run();
