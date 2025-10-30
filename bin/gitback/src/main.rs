use chrono::prelude::*;
use futures::stream::{self, StreamExt};
use git2::{Cred, FetchOptions, RemoteCallbacks, Repository};
use octocrab::Octocrab;
use std::process::{Command, ExitStatus};
use tempfile::TempDir;

async fn clone_repo(
    owner: &str,
    repo: &str,
    path: &std::path::Path,
    token: &str,
) -> Result<(), anyhow::Error> {
    let git = Octocrab::builder().personal_token(token).build()?;

    let mut callbacks = RemoteCallbacks::new();
    callbacks.credentials(|_url, _username_from_url, _allowed_types| {
        Cred::userpass_plaintext("git", token)
    });

    let mut fo = FetchOptions::new();
    fo.remote_callbacks(callbacks);

    {
        let mut builder = git2::build::RepoBuilder::new();
        builder.fetch_options(fo);

        let git_repo = git.repos(owner, repo).get().await?;
        builder.clone(
            &git_repo.clone_url.unwrap().to_string(),
            path.join(repo).as_path(),
        )?;
    }

    {
        let mut callbacks = RemoteCallbacks::new();
        callbacks.credentials(|_url, _username_from_url, _allowed_types| {
            Cred::userpass_plaintext("git", token)
        });

        let mut fo = FetchOptions::new();
        fo.remote_callbacks(callbacks);
        let git_repo = Repository::open(
            path.join(repo)
                .as_path()
                .to_str()
                .ok_or(anyhow::anyhow!("Failed to create repo path"))?,
        )?;

        let remotes = git_repo.remotes()?;
        for remote_name in remotes.iter().flatten() {
            let mut remote = git_repo.find_remote(remote_name)?;
            remote.fetch(&[] as &[&str], Some(&mut fo), None)?;
        }
    }

    Ok(())
}

fn create_zst(dir: &std::path::Path, outf: &str) -> Result<ExitStatus, anyhow::Error> {
    tracing::info!("creating {outf}");
    Ok(Command::new("bsdtar")
        .args([
            "--zstd",
            "-cf",
            outf,
            "-C",
            dir.parent()
                .ok_or(anyhow::anyhow!("Failed to get parent path"))?
                .to_str()
                .ok_or(anyhow::anyhow!("Failed to convert Path to str"))?,
            ".",
        ])
        .status()?)
}

fn upload_zst(zst: &str, upload_path: &str) -> Result<ExitStatus, anyhow::Error> {
    tracing::info!("uploading {zst} to {upload_path}");
    Ok(Command::new("aws")
        .args(["s3", "cp", zst, upload_path])
        .status()?)
}

#[tokio::main]
async fn main() -> Result<(), anyhow::Error> {
    let subscriber = tracing_subscriber::fmt()
        .compact()
        .with_file(true)
        .with_line_number(true)
        .with_target(true)
        .finish();
    tracing::subscriber::set_global_default(subscriber)?;

    let token = std::env::var("GITHUB_TOKEN").expect("GITHUB_TOKEN env variable is required");
    let token = token.trim();

    let gh_org = std::env::var("GH_ORG").unwrap_or("curibio".to_string());

    let bucket = std::env::var("S3_BUCKET").unwrap_or("curibio-backup".to_string());
    let prefix = std::env::var("S3_PREFIX").unwrap_or("github".to_string());
    let upload_path = format!("s3://{bucket}/{prefix}");

    let datetime = Utc::now().format("%Y-%m-%d").to_string();
    let zst_file = format!("repos_{}.zst", datetime);

    tracing::info!("Starting backup for org {gh_org}, uploading {zst_file} to {upload_path}");

    let temp_dir = TempDir::new()?;
    let temp_dir_path = temp_dir.path().join("repos");
    let temp_dir_path = temp_dir_path.as_path();

    let git = Octocrab::builder().personal_token(token).build()?;
    let org_repos = git.orgs(gh_org).list_repos().per_page(255).send().await?;

    let mut repos = Vec::new();
    for repo in org_repos {
        repos.push(repo);
    }

    stream::iter(repos)
        .for_each_concurrent(5, |repo| async move {
            tracing::info!("cloning {:?} to {:?}", repo.name, temp_dir_path);
            let result = clone_repo("curibio", &repo.name, temp_dir_path, token).await;
            if result.is_err() {
                tracing::error!("failed cloning {}", repo.name);
            }
        })
        .await;

    let _ = create_zst(temp_dir_path, &zst_file);
    let _ = upload_zst(&zst_file, &upload_path);

    Ok(())
}
