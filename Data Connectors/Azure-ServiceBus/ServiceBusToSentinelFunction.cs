using System;
using System.Linq;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using Azure.Core;
using Azure.Identity;
using Newtonsoft.Json;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Extensions.Logging;
using Azure.Messaging.ServiceBus;

namespace YourServiceBus;

public class ServiceBusToSentinelFunction
{
    private readonly HttpClient _httpClient;
    private readonly ILogger<ServiceBusToSentinelFunction> _logger;
    private readonly ManagedIdentityCredential _credential;
    private readonly string   _dceBaseUrl;          // unique DCE
    private readonly string[] _dcrIds;              // multiple DCRs
    private readonly string   _streamName;
    private static readonly Random _rng = Random.Shared;

    public ServiceBusToSentinelFunction(
        ILogger<ServiceBusToSentinelFunction> logger,
        IHttpClientFactory httpClientFactory)
    {
        _logger     = logger;
        _httpClient = httpClientFactory.CreateClient();
        _credential = new ManagedIdentityCredential();

        _dceBaseUrl = GetEnv("DCE_BASE_URL").TrimEnd('/');
        _streamName = GetEnv("STREAM_NAME");
        _dcrIds     = GetEnv("DCR_IDS")
                        .Split(';', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);

        if (_dcrIds.Length == 0)
            throw new InvalidOperationException("DCR_IDS must have at least one ID.");
    }

    private static string GetEnv(string name) =>
        Environment.GetEnvironmentVariable(name)
        ?? throw new InvalidOperationException($"App Setting {name} not configured.");

    [Function(nameof(ServiceBusToSentinelFunction))]
    public async Task Run(
        [ServiceBusTrigger(
            "%SB_TOPIC_NAME%",
            "%SB_SUBSCRIPTION_NAME%",
            Connection = "ServiceBusConnection",
            IsBatched = true)]
        ServiceBusReceivedMessage[] messages)
    {
        // payload in array – format required by api-version=2023-01-01
        var payloadArray = messages.Select(m => new
        {
            RawMessage    = m.Body.ToString(),
            TimeGenerated = DateTime.UtcNow        // optional
        });

        string jsonPayload = JsonConvert.SerializeObject(payloadArray);

        try
        {
            await SendToRandomDcrAsync(jsonPayload);
            // autoCompleteMessages=true ⇒ functions complete messages automatically
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to send batch; it will be redelivered.");
            throw;   // forces the abandon of the batch
        }
    }

    private Task SendToRandomDcrAsync(string json) =>
        SendToDcrAsync(_dcrIds[_rng.Next(_dcrIds.Length)], json);

    private async Task SendToDcrAsync(string dcrId, string json)
    {
        const string scope = "https://monitor.azure.com/.default";
        var token = await _credential.GetTokenAsync(new TokenRequestContext(new[] { scope }));

        var endpoint =
            $"{_dceBaseUrl}/dataCollectionRules/{dcrId}/streams/{_streamName}?api-version=2023-01-01";

        using var req = new HttpRequestMessage(HttpMethod.Post, endpoint)
        {
            Content = new StringContent(json, Encoding.UTF8, "application/json")
        };
        req.Headers.Authorization =
            new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", token.Token);

        var resp = await _httpClient.SendAsync(req);
        if (!resp.IsSuccessStatusCode)
        {
            var body = await resp.Content.ReadAsStringAsync();
            throw new InvalidOperationException($"DCR {dcrId} → {resp.StatusCode}: {body}");
        }
    }
}