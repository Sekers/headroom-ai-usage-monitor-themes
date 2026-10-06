//! Headroom engine test: loads every theme in THEME_PACK_DIR through Claude Code Usage Monitor's own
//! loader, renders it with its own engine for many account and provider mixes, checks the widget
//! width, and saves PNGs to THEME_PACK_OUT. Copy into a checkout as `src/theme_engine/pack_tests.rs`;
//! see the README next to this file.
use super::*;
use crate::accounts::{AccountProfile, AccountSettings, ProviderAccounts};
use crate::models::{AccountUsage, UsageData, UsageSection};
use std::time::{Instant, SystemTime};

#[derive(Clone, Copy)]
enum Slot {
    /// 5-hour and weekly (percentage, seconds until reset); None = no such window.
    Ok(Option<(f64, i64)>, Option<(f64, i64)>, bool),
    Error,
    Loading,
}

#[derive(Clone, Copy)]
struct Acct {
    provider: ProviderId,
    id: &'static str,
    name: &'static str,
    slot: Slot,
}

const C: ProviderId = ProviderId::Claude;
const X: ProviderId = ProviderId::Codex;

fn sample(i: usize) -> Slot {
    match i % 3 {
        0 => Slot::Ok(Some((34.0, 3 * 3600)), Some((41.0, 3 * 86400)), false),
        1 => Slot::Ok(Some((82.0, 3600)), Some((63.0, 5 * 86400)), false),
        _ => Slot::Ok(Some((95.0, 22 * 60)), Some((88.0, 2 * 86400)), false),
    }
}

/// Accounts in the order they were added: (provider, id, name).
fn accounts(list: &[(ProviderId, &'static str, &'static str)]) -> Vec<Acct> {
    list.iter()
        .enumerate()
        .map(|(i, &(provider, id, name))| Acct { provider, id, name, slot: sample(i) })
        .collect()
}

fn mix(claude: usize, codex: usize) -> Vec<Acct> {
    const CLAUDE: [(&str, &str); 5] =
        [("default", "PER"), ("account_1", "WRK"), ("account_2", "LAB"), ("account_3", "ALT"), ("account_4", "OLD")];
    const CODEX: [(&str, &str); 5] =
        [("default", "CDX"), ("account_1", "TEAM"), ("account_2", "OSS"), ("account_3", "SIDE"), ("account_4", "LAST")];
    let mut list = Vec::new();
    list.extend(CLAUDE[..claude].iter().map(|&(id, name)| (C, id, name)));
    list.extend(CODEX[..codex].iter().map(|&(id, name)| (X, id, name)));
    accounts(&list)
}

fn section(reading: Option<(f64, i64)>, now: SystemTime) -> UsageSection {
    match reading {
        Some((percentage, seconds)) => UsageSection {
            available: true,
            percentage,
            resets_at: Some(if seconds >= 0 {
                now + Duration::from_secs(seconds as u64)
            } else {
                now - Duration::from_secs((-seconds) as u64)
            }),
        },
        None => UsageSection::default(),
    }
}

fn usage_for(accts: &[Acct], extras: &[(ProviderId, Slot)]) -> AppUsageData {
    let now = SystemTime::now();
    let mut settings = AccountSettings::default();
    let mut data = AppUsageData::default();
    for provider in [C, X] {
        let mine: Vec<&Acct> = accts.iter().filter(|a| a.provider == provider).collect();
        if mine.is_empty() {
            continue;
        }
        let mut configured = ProviderAccounts { profiles: Vec::new(), ..Default::default() };
        for (index, acct) in mine.iter().enumerate() {
            let profile = AccountProfile {
                id: acct.id.into(),
                name: acct.name.into(),
                config_dir: format!("C:\\acct{index}"),
                ..Default::default()
            };
            configured.profiles.push(profile.clone());
            configured.used_ids.insert(profile.id.clone());
            let (usage, error) = match acct.slot {
                Slot::Ok(five, week, stale) => (
                    Some(UsageData { session: section(five, now), weekly: section(week, now), stale, ..Default::default() }),
                    None,
                ),
                Slot::Error => (None, Some(crate::poller::PollError::HttpStatus(429))),
                Slot::Loading => (None, None),
            };
            data.accounts.push(AccountUsage {
                provider,
                profile,
                source_signature: "fixture".into(),
                source_path: None,
                selected: false,
                usage,
                error,
            });
        }
        configured.selected = mine[0].id.into();
        match provider {
            ProviderId::Claude => settings.claude = configured,
            _ => settings.codex = configured,
        }
    }
    data.select_accounts(&settings);
    // Providers with a single, unnamed account: their reading goes straight in, if they have one.
    for &(provider, slot) in extras {
        if let Slot::Ok(five, week, stale) = slot {
            data.insert(provider, UsageData { session: section(five, now), weekly: section(week, now), stale, ..Default::default() });
        }
    }
    data
}

fn hover(theme: &ThemeDocument) -> ThemeDocument {
    let surface = &theme.surfaces[0];
    let source = surface.mouse_events.as_ref().unwrap().handler(MouseEventKind::MouseEnter).to_string();
    let mut overrides = HashMap::new();
    for action in parse_mouse_actions(&source).expect("mouse_enter parses") {
        let MouseAction::Set { target: MouseActionTarget::Object(id), property, value } = action else {
            panic!("unexpected hover action {action:?}");
        };
        overrides.insert(MouseActionOverrideKey { surface_index: 0, object_id: id, property }, value);
    }
    apply_mouse_action_overrides(theme, &overrides)
}

fn save(rendered: &RenderedTheme, path: &Path, dark: bool) {
    let background: [u32; 3] = if dark { [0x20, 0x20, 0x20] } else { [0xEE, 0xEE, 0xEE] };
    let mut rgb = Vec::with_capacity(rendered.pixels.len() * 3);
    for pixel in &rendered.pixels {
        let a = pixel >> 24;
        for (shift, bg) in [(16, background[0]), (8, background[1]), (0, background[2])] {
            let premultiplied = (pixel >> shift) & 0xFF;
            rgb.push((premultiplied + bg * (255 - a) / 255).min(255) as u8);
        }
    }
    image::RgbImage::from_raw(rendered.width, rendered.height, rgb).unwrap().save(path).unwrap();
}

/// Save the tray icon as Windows would show it at 16, 24 and 32 px, with its transparency kept.
fn save_tray(rendered: &RenderedTheme, out: &Path, stem: &str, mode: &str) {
    let mut rgba = Vec::with_capacity(rendered.pixels.len() * 4);
    for pixel in &rendered.pixels {
        let a = (pixel >> 24) & 0xFF;
        let straight = |c: u32| if a == 0 { 0 } else { ((c * 255 + a / 2) / a).min(255) as u8 };
        rgba.extend([straight((pixel >> 16) & 0xFF), straight((pixel >> 8) & 0xFF), straight(pixel & 0xFF), a as u8]);
    }
    let icon = image::RgbaImage::from_raw(rendered.width, rendered.height, rgba).unwrap();
    for size in [16, 24, 32] {
        image::imageops::resize(&icon, size, size, image::imageops::FilterType::Triangle)
            .save(out.join(format!("{stem}__tray{size}__{mode}.png")))
            .unwrap();
    }
}

/// The widget width each design should take for `count` accounts.
fn expected_width(theme_id: &str, count: usize) -> u32 {
    match theme_id {
        "headroom-lanes" => 145,
        "headroom-cells" | "headroom-cells-horizon" => match count.min(6) as u32 { 0 => 30, n => 32 * n - 2 },
        "headroom-pills" => match count.min(6) as u32 { 0 => 60, n => 63 * n - 3 },
        other => panic!("unknown theme {other}"),
    }
}

#[test]
fn theme_pack_validates_and_renders() {
    let (Ok(pack), Ok(out)) = (std::env::var("THEME_PACK_DIR"), std::env::var("THEME_PACK_OUT")) else {
        eprintln!("THEME_PACK_DIR / THEME_PACK_OUT not set; skipping");
        return;
    };
    let (pack, out) = (PathBuf::from(pack), PathBuf::from(out));
    std::fs::create_dir_all(&out).unwrap();
    let dark = crate::theme::is_dark_mode();
    let mode = if dark { "dark" } else { "light" };
    let runtime = ThemeRuntime::new(true, true, false);

    let ok = |five, week| Slot::Ok(Some(five), Some(week), false);
    let mut scenarios: Vec<(String, Option<Vec<Acct>>, ThemeRuntime)> = Vec::new();
    for (claude, codex) in [(1, 0), (2, 0), (3, 0), (0, 1), (0, 2), (0, 3), (1, 1), (2, 1), (1, 2), (2, 2), (3, 3), (4, 3)] {
        scenarios.push((format!("c{claude}x{codex}"), Some(mix(claude, codex)), runtime));
    }
    // Removed accounts leave gaps in the IDs: Claude account_1 and Codex default are gone.
    scenarios.push(("gaps".into(), Some(accounts(&[(C, "default", "PER"), (C, "account_2", "LAB"), (X, "account_1", "TEAM")])), runtime));
    // Only IDs late in the list.
    scenarios.push(("late-ids".into(), Some(accounts(&[(C, "account_4", "OLD"), (X, "account_3", "SIDE")])), runtime));
    scenarios.push(("no-accounts".into(), Some(Vec::new()), runtime));
    scenarios.push(("no-data".into(), None, runtime));
    // Names CodeZeno gave the accounts, plus one whose name was cleared (it falls back to the ID).
    scenarios.push((
        "default-names".into(),
        Some(accounts(&[(C, "default", "Default"), (C, "account_1", "Account 1"), (C, "account_2", "account_2"), (X, "default", "Default")])),
        runtime,
    ));
    // Weekly limits running high while the 5-hour windows are low.
    let weekly = |five: f64, week: f64| Slot::Ok(Some((five, 3 * 3600)), Some((week, 2 * 86400)), false);
    let mut weekly_high = mix(2, 1);
    weekly_high[0].slot = weekly(21.0, 80.0);
    weekly_high[1].slot = weekly(30.0, 100.0);
    weekly_high[2].slot = weekly(10.0, 60.0);
    scenarios.push(("weekly-high".into(), Some(weekly_high), runtime));
    let base = mix(2, 1);
    let with = |changes: &[(usize, Slot)]| {
        let mut list = base.clone();
        for &(i, slot) in changes {
            list[i].slot = slot;
        }
        Some(list)
    };
    scenarios.push((
        "states".into(),
        with(&[(0, Slot::Ok(Some((34.0, 3 * 3600)), Some((41.0, 3 * 86400)), true)), (2, Slot::Ok(None, Some((12.0, 6 * 86400)), false))]),
        runtime,
    ));
    scenarios.push(("reset".into(), with(&[(1, ok((100.0, -60), (63.0, 5 * 86400)))]), runtime));
    scenarios.push(("error-loading".into(), with(&[(0, Slot::Error), (2, Slot::Loading)]), runtime.with_poll_state(true, true)));
    // The account closest to its limits has no 5-hour window.
    scenarios.push(("no-5h-closest".into(), with(&[(2, Slot::Ok(None, Some((95.0, 2 * 86400)), false))]), runtime));
    scenarios.push(("all-failed".into(), with(&[(0, Slot::Error), (1, Slot::Error), (2, Slot::Error)]), runtime.with_poll_state(false, true)));
    scenarios.push(("remaining".into(), Some(base.clone()), runtime.with_countdown(true)));
    let long: Vec<Acct> = accounts(&[(C, "default", "WORK"), (C, "account_1", "HOME"), (X, "default", "TEAM")])
        .into_iter()
        .map(|a| Acct { slot: ok((100.0, 59 * 60), (100.0, 6 * 86400)), ..a })
        .collect();
    let long_reset: Vec<Acct> = long.iter().map(|a| Acct { slot: ok((100.0, -60), (100.0, -60)), ..*a }).collect();
    scenarios.push(("long".into(), Some(long), runtime));
    scenarios.push(("long-reset-remaining".into(), Some(long_reset), runtime.with_countdown(true)));

    // Every scenario so far has only Claude and Codex turned on. The rest turn on other providers.
    let mut scenarios: Vec<(String, Option<Vec<Acct>>, ThemeRuntime, Vec<(ProviderId, Slot)>)> =
        scenarios.into_iter().map(|(name, accts, runtime)| (name, accts, runtime, Vec::new())).collect();
    use crate::providers::ProviderSet;
    use ProviderId::{Antigravity, Copilot, Cursor, Grok, OpenCode};
    let only = |set: &[ProviderId]| ThemeRuntime::from_providers(ProviderSet::from_enabled(set.iter().copied()));
    let pool = |pct: f64, seconds: i64| Slot::Ok(None, Some((pct, seconds)), false);
    let others = vec![
        (Antigravity, ok((40.0, 2 * 3600), (20.0, 4 * 86400))),
        (OpenCode, ok((55.0, 3600), (30.0, 6 * 86400))),
        (Cursor, ok((70.0, 12 * 86400), (15.0, 12 * 86400))),
        (Grok, pool(85.0, 20 * 86400)),
        (Copilot, pool(92.0, 9 * 86400)),
    ];
    scenarios.push(("all-providers".into(), Some(mix(1, 1)), only(&[C, X, Antigravity, OpenCode, Cursor, Grok, Copilot]), others.clone()));
    scenarios.push(("providers-only".into(), Some(Vec::new()), only(&[Cursor, Grok, Copilot]), others[2..].to_vec()));
    scenarios.push(("provider-no-data".into(), Some(mix(1, 0)), only(&[C, Cursor]), vec![(Cursor, Slot::Loading)]));

    let mut problems = Vec::new();
    let mut files: Vec<PathBuf> = std::fs::read_dir(&pack)
        .unwrap()
        .map(|entry| entry.unwrap().path())
        .filter(|path| path.extension().is_some_and(|ext| ext == "json"))
        .collect();
    files.sort();
    let (mut rendered_count, mut slowest) = (0, (Duration::ZERO, String::new()));
    for path in &files {
        let theme = match theme_storage::load_theme(path) {
            Ok(theme) => theme,
            Err(error) => {
                problems.push(format!("{}: load_theme failed: {error}", path.display()));
                continue;
            }
        };
        let hovered_theme = hover(&theme);
        for (name, accts, runtime, extras) in &scenarios {
            let data = accts.as_ref().map(|list| usage_for(list, extras));
            let count = accts.as_ref().map_or(0, Vec::len) + extras.len();
            let (width, _) = resolve_surface_content_size(&theme, 0, data.as_ref(), *runtime);
            let expected = expected_width(&theme.id, count);
            if width != expected {
                problems.push(format!("{} {name}: width {width}, expected {expected}", theme.id));
            }
            // The tray icon: it must render cleanly and never come out blank.
            let tray = theme.surfaces.iter().position(|surface| surface.id == "shared-tray-icon").unwrap();
            let rendered = render_theme_surface_with_runtime_at_scale(&theme, tray, data.as_ref(), *runtime, 1.0);
            rendered_count += 1;
            for warning in &rendered.warnings {
                problems.push(format!("{} {name} tray: {warning}", theme.id));
            }
            if rendered.pixels.iter().all(|pixel| pixel >> 24 == 0) {
                problems.push(format!("{} {name} tray: blank icon", theme.id));
            }
            save_tray(&rendered, &out, &format!("{}__{name}", theme.id), mode);
            for (hovered, effective) in [(false, &theme), (true, &hovered_theme)] {
                for scale in [1.0, 1.25, 1.5, 1.75, 2.0] {
                    let started = Instant::now();
                    let rendered = render_theme_surface_with_runtime_at_scale(effective, 0, data.as_ref(), *runtime, scale);
                    let elapsed = started.elapsed();
                    if elapsed > slowest.0 {
                        slowest = (elapsed, format!("{} {name} @{scale}", theme.id));
                    }
                    rendered_count += 1;
                    for warning in &rendered.warnings {
                        problems.push(format!("{} {name} hover={hovered} @{scale}: {warning}", theme.id));
                    }
                    if scale == 1.75 {
                        let suffix = if hovered { "-hover" } else { "" };
                        save(&rendered, &out.join(format!("{}__{name}{suffix}__{mode}.png", theme.id)), dark);
                    }
                }
            }
        }
    }
    eprintln!(
        "pack: {} themes, {} renders, {} problems, slowest render {:?} ({})",
        files.len(),
        rendered_count,
        problems.len(),
        slowest.0,
        slowest.1
    );
    assert!(problems.is_empty(), "{}", problems.join("\n"));
}

/// Average render time per theme in THEME_TIMING_DIR, with 2 Claude + 1 Codex accounts.
#[test]
fn theme_render_timing() {
    let Ok(dir) = std::env::var("THEME_TIMING_DIR") else {
        return;
    };
    let data = usage_for(&mix(2, 1), &[]);
    let runtime = ThemeRuntime::new(true, true, false);
    let mut files: Vec<PathBuf> = std::fs::read_dir(dir).unwrap().map(|e| e.unwrap().path()).collect();
    files.sort();
    for path in files {
        let theme = theme_storage::load_theme(&path).unwrap();
        for scale in [1.0, 2.0] {
            let _ = render_theme_surface_with_runtime_at_scale(&theme, 0, Some(&data), runtime, scale);
            let runs = 20;
            let started = Instant::now();
            for _ in 0..runs {
                let _ = render_theme_surface_with_runtime_at_scale(&theme, 0, Some(&data), runtime, scale);
            }
            eprintln!("{:<32} @{scale}: {:>6.1} ms", path.file_name().unwrap().to_string_lossy(), started.elapsed().as_secs_f64() * 1000.0 / runs as f64);
        }
    }
}
