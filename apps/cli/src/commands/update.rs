use anyhow::Result;
use clap::Args;
use colored::Colorize;
use indicatif::{ProgressBar, ProgressStyle};
use std::path::PathBuf;
use std::time::Duration;

use crate::client::{ApiClient, UpdateRequest};
use crate::output::OutputFormat;

#[derive(Args, Debug)]
pub struct UpdateArgs {
    /// Path to the existing .dir.json file
    #[arg()]
    pub dir_file: PathBuf,

    /// What changed / how to update the diagram
    #[arg(short, long)]
    pub feedback: String,

    /// Output file path (overwrites derived SVG path if not specified)
    #[arg(short, long)]
    pub output: Option<PathBuf>,

    /// Complexity level to render
    #[arg(long)]
    pub detail: Option<String>,
}

pub async fn run(args: UpdateArgs, client: ApiClient, output_format: OutputFormat) -> Result<()> {
    let dir_json = std::fs::read_to_string(&args.dir_file)?;
    let dir: serde_json::Value = serde_json::from_str(&dir_json)?;

    let pb = match output_format {
        OutputFormat::Human => {
            let pb = ProgressBar::new_spinner();
            pb.set_style(
                ProgressStyle::default_spinner()
                    .template("{spinner:.cyan} {msg}")
                    .unwrap(),
            );
            pb.set_message("Updating diagram...");
            pb.enable_steady_tick(Duration::from_millis(80));
            Some(pb)
        }
        OutputFormat::Json => None,
    };

    let req = UpdateRequest {
        dir,
        feedback: args.feedback,
        complexity: args.detail,
    };

    let response = client.update(req).await?;

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
            let out_path = args
                .output
                .as_ref()
                .cloned()
                .unwrap_or_else(|| args.dir_file.with_extension("").with_extension("svg"));

            std::fs::write(&out_path, &response.svg)?;
            println!("{} {}", "SVG updated:".green(), out_path.display());

            // Update DIR file in place
            std::fs::write(&args.dir_file, serde_json::to_string_pretty(&response.dir)?)?;
            println!("{} {}", "DIR updated:".green(), args.dir_file.display());
        }
    }

    Ok(())
}
