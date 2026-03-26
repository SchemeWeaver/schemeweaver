use clap::{Parser, Subcommand};

mod commands;
mod client;
mod output;

#[derive(Parser)]
#[command(name = "schemeweaver")]
#[command(about = "Generate semantic SVG diagrams from prompts", long_about = None)]
#[command(version)]
struct Cli {
    /// API server URL
    #[arg(long, env = "SCHEMEWEAVER_API_URL", default_value = "http://localhost:8000")]
    api_url: String,

    /// Output format
    #[arg(long, default_value = "human")]
    output: output::OutputFormat,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Generate a diagram from a prompt
    Generate(commands::generate::GenerateArgs),
    /// Update an existing diagram with new context
    Update(commands::update::UpdateArgs),
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();
    let client = client::ApiClient::new(&cli.api_url);

    match cli.command {
        Commands::Generate(args) => commands::generate::run(args, client, cli.output).await,
        Commands::Update(args) => commands::update::run(args, client, cli.output).await,
    }
}
