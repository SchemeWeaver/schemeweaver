use anyhow::Result;
use clap::Args;
use colored::Colorize;
use indicatif::{ProgressBar, ProgressStyle};
use std::path::PathBuf;
use std::time::Duration;

use crate::client::{ApiClient, GenerateRequest};
use crate::output::OutputFormat;

#[derive(Args, Debug)]
pub struct GenerateArgs {
    /// Natural language description of the diagram
    #[arg(short, long)]
    pub prompt: String,

    /// Output file path (default: stdout)
    #[arg(short, long)]
    pub output: Option<PathBuf>,

    /// Also save the DIR JSON alongside the SVG
    #[arg(long)]
    pub save_dir: bool,

    /// Complexity level to render: low, medium, high (default: interactive with all levels)
    #[arg(long)]
    pub detail: Option<String>,

    /// Extra context for the diagram
    #[arg(long)]
    pub context: Option<String>,
}

pub async fn run(args: GenerateArgs, client: ApiClient, output_format: OutputFormat) -> Result<()> {
    let pb = match output_format {
        OutputFormat::Human => {
            let pb = ProgressBar::new_spinner();
            pb.set_style(
                ProgressStyle::default_spinner()
                    .template("{spinner:.cyan} {msg}")
                    .unwrap(),
            );
            pb.set_message("Generating diagram...");
            pb.enable_steady_tick(Duration::from_millis(80));
            Some(pb)
        }
        OutputFormat::Json => None,
    };

    let req = GenerateRequest {
        prompt: args.prompt.clone(),
        context: args.context,
        complexity: args.detail,
    };

    let response = client.generate(req).await?;

    if let Some(pb) = &pb {
        pb.finish_and_clear();
    }

    match output_format {
        OutputFormat::Json => {
            println!(
                "{}",
                serde_json::to_string_pretty(&serde_json::json!({
                    "svg": response.svg,
                    "dir": response.dir,
                    "issues": response.issues,
                }))?
            );
        }
        OutputFormat::Human => {
            // Write SVG
            match &args.output {
                Some(path) => {
                    std::fs::write(path, &response.svg)?;
                    println!("{} {}", "SVG written to".green(), path.display());
                }
                None => {
                    print!("{}", response.svg);
                }
            }

            // Optionally save DIR
            if args.save_dir {
                if let Some(path) = &args.output {
                    let dir_path = path.with_extension("dir.json");
                    std::fs::write(&dir_path, serde_json::to_string_pretty(&response.dir)?)?;
                    println!("{} {}", "DIR saved to".green(), dir_path.display());
                }
            }

            // Report issues
            if !response.issues.is_empty() {
                println!("{}", "\nAccessibility issues:".yellow());
                for issue in &response.issues {
                    println!("  {} {}", "WARNING".yellow(), issue);
                }
            }
        }
    }

    Ok(())
}
