use anyhow::Result;
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize)]
pub struct GenerateRequest {
    pub prompt: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub context: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub complexity: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct GenerateResponse {
    pub svg: String,
    pub dir: serde_json::Value,
    pub issues: Vec<String>,
}

#[derive(Debug, Serialize)]
pub struct UpdateRequest {
    pub dir: serde_json::Value,
    pub feedback: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub complexity: Option<String>,
}

pub struct ApiClient {
    base_url: String,
    client: reqwest::Client,
}

impl ApiClient {
    pub fn new(base_url: &str) -> Self {
        Self {
            base_url: base_url.trim_end_matches('/').to_string(),
            client: reqwest::Client::new(),
        }
    }

    pub async fn generate(&self, req: GenerateRequest) -> Result<GenerateResponse> {
        let res = self
            .client
            .post(format!("{}/v1/generate", self.base_url))
            .json(&req)
            .send()
            .await?
            .error_for_status()?
            .json::<GenerateResponse>()
            .await?;
        Ok(res)
    }

    pub async fn update(&self, req: UpdateRequest) -> Result<GenerateResponse> {
        let res = self
            .client
            .post(format!("{}/v1/update", self.base_url))
            .json(&req)
            .send()
            .await?
            .error_for_status()?
            .json::<GenerateResponse>()
            .await?;
        Ok(res)
    }
}
