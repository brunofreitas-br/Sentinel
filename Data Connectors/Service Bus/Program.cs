using Microsoft.Azure.Functions.Worker.Builder;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

var builder = FunctionsApplication.CreateBuilder(args);

// Registra HttpClient para ser injetado na Function
builder.Services.AddHttpClient();

// (Removida a chamada a AddApplicationInsightsTelemetryWorkerService)
// para evitar o erro de extensão inexistente

builder.ConfigureFunctionsWebApplication();

builder.Build().Run();