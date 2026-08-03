# Task 2 report: `preference_model.py` writes a metadata sidecar

**Status:** DONE
**Branch:** `feat/preference-toggle`
**Commit:** `61a4554b214164bdb639f1090ee2040c7321af41`
**Parent commit:** `a42a074` (Task 1, already on branch)
**Plan:** `docs/superpowers/plans/2026-07-10-preference-toggle.md` Task 2
**Brief:** `.superpowers/sdd/task-2-brief.md`

## Commands run

```bash
# 1. Step 1: appended the failing test to tests/test_preference_model.py
#    (via Edit tool, appending lines 76-108 to the existing 73-line file)

# 2. Step 2: confirm the new test fails for the right reason
PYTHONPATH=src uv run pytest tests/test_preference_model.py::test_main_writes_metadata_sidecar_on_successful_train -v

# 3. Step 3: implemented by editing src/clawmarks/search/preference_model.py
#    (added `import os` and `from datetime import datetime, timezone`,
#     added `MODEL_META_FILE = SWEEP_DIR / "preference_model_meta.json"`,
#     added the meta dict + tmp-then-os.replace write after joblib.dump,
#     updated the success print to include the sidecar path)

# 4. Step 4: confirm the full file's tests pass
PYTHONPATH=src uv run pytest tests/test_preference_model.py -v

# 4b. Also ran the full suite to make sure nothing else regressed
PYTHONPATH=src uv run pytest tests/ -v

# 5. Em-dash / "-- " check
git diff --no-color | rg -n -e '—' -e ' -- ' || echo "NO EM DASHES OR -- FOUND"

# 6. Commit
git add src/clawmarks/search/preference_model.py tests/test_preference_model.py
git commit -m "feat(clawmarks): write preference model metadata sidecar on train"
```

## Step 2 output (new test fails for the right reason)

```
============================= test session starts ==============================
platform linux -- Python 3.14.6, pytest-9.1.0, pluggy-1.6.0 -- /workspace/trent-with-smart-prompts/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /workspace/trent-with-smart-prompts
configfile: pyproject.toml
collecting ... collected 1 item

tests/test_preference_model.py::test_main_writes_metadata_sidecar_on_successful_train FAILED [100%]

=================================== FAILURES ===================================
____________ test_main_writes_metadata_sidecar_on_successful_train _____________

tmp_path = PosixPath('/tmp/pytest-of-node/pytest-97/test_main_writes_metadata_sidecar_on_successful_train0')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x7f1240705940>

    def test_main_writes_metadata_sidecar_on_successful_train(tmp_path, monkeypatch):
        from clawmarks.search import embed_cache
    
        rng = np.random.RandomState(0)
        yes_cluster = rng.normal(loc=5.0, scale=0.1, size=(30, 2))
        no_cluster = rng.normal(loc=-5.0, scale=0.1, size=(30, 2))
        embeddings = np.vstack([yes_cluster, no_cluster]).astype(np.float32)
        tags = [f"t{i}" for i in range(60)]
        embed_cache.save_cache(tmp_path / "embeddings.npz", tags, embeddings)
    
        ratings = {tags[i]: {"label": "yes" if i < 30 else "no", "rated_at": "t"} for i in range(60)}
        (tmp_path / "user_ratings.json").write_text(json.dumps(ratings))
    
        monkeypatch.setattr(preference_model, "SWEEP_DIR", tmp_path)
        monkeypatch.setattr(preference_model.embed_cache, "EMBEDDINGS_FILE", tmp_path / "embeddings.npz")
        monkeypatch.setattr(preference_model, "MODEL_FILE", tmp_path / "preference_model.joblib")
>       monkeypatch.setattr(preference_model, "MODEL_META_FILE", tmp_path / "preference_model_meta.json")
E       AttributeError: <module 'clawmarks.search.preference_model' from '/workspace/trent-with-smart-prompts/src/clawmarks/search/preference_model.py'> has no attribute 'MODEL_META_FILE'

tests/test_preference_model.py:98: AttributeError
=========================== short test summary info ============================
FAILED tests/test_preference_model.py::test_main_writes_metadata_sidecar_on_successful_train
============================== 1 failed in 1.96s ===============================
```

Failure mode matches the brief's expectation exactly: `AttributeError: ... has no attribute 'MODEL_META_FILE'`, on the `monkeypatch.setattr(preference_model, "MODEL_META_FILE", ...)` line.

## Step 4 output (tests/test_preference_model.py -v)

```
============================= test session starts ==============================
platform linux -- Python 3.14.6, pytest-9.1.0, pluggy-1.6.0 -- /workspace/trent-with-smart-prompts/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /workspace/trent-with-smart-prompts
configfile: pyproject.toml
collecting ... collected 10 items

tests/test_preference_model.py::test_build_training_set_uses_only_tags_present_in_both_embeddings_and_ratings PASSED [ 10%]
tests/test_preference_model.py::test_build_training_set_skips_unrecognized_labels PASSED [ 20%]
tests/test_preference_model.py::test_train_and_predict_proba_separates_obviously_different_clusters PASSED [ 30%]
tests/test_preference_model.py::test_cross_validate_returns_a_valid_accuracy_using_leave_one_out_below_min_labels PASSED [ 40%]
tests/test_preference_model.py::test_class_balance_error_flags_an_all_yes_label_set PASSED [ 50%]
tests/test_preference_model.py::test_class_balance_error_flags_an_all_no_label_set PASSED [ 60%]
tests/test_preference_model.py::test_class_balance_error_flags_a_minority_class_below_the_fold_count PASSED [ 70%]
tests/test_preference_model.py::test_class_balance_error_allows_a_well_balanced_label_set PASSED [ 80%]
tests/test_preference_model.py::test_class_balance_error_allows_an_imbalanced_but_above_fold_count_label_set_below_min_labels PASSED [ 90%]
tests/test_preference_model.py::test_main_writes_metadata_sidecar_on_successful_train PASSED [100%]

=============================== warnings summary ===============================
tests/test_preference_model.py: 17 warnings
  /workspace/trent-with-smart-prompts/.venv/lib/python3.14/site-packages/sklearn/linear_model/_logistic.py:451: OptimizeWarning: Unknown solver options: iprint
    opt_res = optimize.minimize(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 10 passed, 17 warnings in 2.03s ========================
```

All 10 tests in the file pass, including the new one. The 17 warnings are pre-existing
`OptimizeWarning: Unknown solver options: iprint` from scikit-learn about the logistic
regression solver, not introduced by this change.

## Full-suite output (tests/ -v, regression check)

```
============================= test session starts ==============================
platform linux -- Python 3.14.6, pytest-9.1.0, pluggy-1.6.0 -- /workspace/trent-with-smart-prompts/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /workspace/trent-with-smart-prompts
configfile: pyproject.toml
collecting ... collected 116 items

tests/test_cli.py::test_build_is_no_longer_a_valid_subcommand PASSED     [  0%]
tests/test_cli.py::test_run_allnight_round_argument_parses PASSED        [  1%]
tests/test_cli.py::test_serve_subcommand_parses PASSED                   [  2%]
tests/test_config.py::test_repo_root_finds_pyproject PASSED              [  3%]
tests/test_config.py::test_repo_root_env_override PASSED                 [  4%]
tests/test_config.py::test_derived_paths_under_repo_root PASSED          [  5%]
tests/test_config.py::test_user_ratings_file_path PASSED                 [  6%]
tests/test_config.py::test_sweep_dir_env_override PASSED                 [  6%]
tests/test_coverage_map.py::test_compute_data_reads_manifest PASSED      [  7%]
tests/test_curation_server.py::test_next_rating_response_returns_item_summary_shape PASSED [  8%]
tests/test_curation_server.py::test_next_rating_response_reports_done_when_all_reviewed PASSED [  9%]
tests/test_curation_server.py::test_record_rating_upserts_with_timestamp PASSED [ 10%]
tests/test_curation_server.py::test_record_rating_overwrites_not_duplicates PASSED [ 11%]
tests/test_curation_server.py::test_record_rating_rejects_invalid_label PASSED [ 12%]
tests/test_curation_server_gallery_route.py::test_gallery_html_served_live PASSED [ 12%]
tests/test_curation_server_lazy_thumbnails.py::test_thumb_generated_on_first_request PASSED [ 13%]
tests/test_curation_server_manifest_cache.py::test_load_manifest_re_reads_when_file_changes PASSED [ 14%]
tests/test_curation_server_manifest_cache.py::test_load_manifest_parses_only_once_under_concurrent_access PASSED [ 15%]
tests/test_curation_server_manifest_cache.py::test_manifest_entry_by_tag_finds_existing_and_missing_tags PASSED [ 16%]
tests/test_curation_server_manifest_cache.py::test_manifest_entry_by_tag_index_rebuilds_on_manifest_change PASSED [ 17%]
tests/test_curation_server_manifest_only_routes_cache.py::test_get_manifest_cached_reuses_cache_across_calls PASSED [ 18%]
tests/test_curation_server_manifest_only_routes_cache.py::test_get_manifest_cached_keeps_targets_independent PASSED [ 18%]
tests/test_curation_server_manifest_only_routes_cache.py::test_archive_route_caches_actual_and_predicted_preference_separately PASSED [ 19%]
tests/test_curation_server_map_redundancy_cache.py::test_get_map_data_is_cached_and_depends_on_solution_map PASSED [ 20%]
tests/test_curation_server_map_redundancy_cache.py::test_get_redundancy_data_is_cached_and_depends_on_solution_map PASSED [ 21%]
tests/test_curation_server_scan_route.py::test_scan_html_reflects_manifest_change_without_rebuild PASSED [ 22%]
tests/test_curation_server_scan_route.py::test_scan_data_json_route PASSED [ 23%]
tests/test_curation_server_solution_map_dep.py::test_get_solution_map_data_uses_live_cache PASSED [ 24%]
tests/test_curation_server_solution_map_dep.py::test_get_solution_map_data_watches_the_final_embeddings_file_too PASSED [ 25%]
tests/test_curation_server_static_assets.py::test_lightbox_js_served_without_being_written_to_disk PASSED [ 25%]
tests/test_curation_server_static_assets.py::test_infotip_js_served_without_being_written_to_disk PASSED [ 26%]
tests/test_elite_archive.py::test_compute_data_uses_yes_rated_images_not_user_picks PASSED [ 27%]
tests/test_elite_archive_live.py::test_compute_data_prefers_yes_rated_image_in_cell PASSED [ 28%]
tests/test_elite_archive_live.py::test_compute_data_falls_back_to_novelty_without_ratings PASSED [ 29%]
tests/test_elite_archive_predicted_preference.py::test_elite_sort_key_falls_back_to_novelty_when_no_predicted_scores PASSED [ 30%]
tests/test_elite_archive_predicted_preference.py::test_elite_sort_key_prefers_predicted_preference_when_available PASSED [ 31%]
tests/test_elite_archive_predicted_preference.py::test_elite_sort_key_treats_missing_score_as_neutral_when_scores_exist_for_others PASSED [ 31%]
tests/test_elite_archive_predicted_preference.py::test_build_item_summary_omits_predicted_preference_when_absent PASSED [ 32%]
tests/test_elite_archive_predicted_preference.py::test_build_item_summary_includes_predicted_preference_when_present PASSED [ 33%]
tests/test_elite_archive_predicted_preference.py::test_sorting_a_cell_with_predicted_scores_puts_highest_score_first PASSED [ 34%]
tests/test_embed_cache.py::test_embed_paths_returns_one_normalized_row_per_path PASSED [ 35%]
tests/test_embed_cache.py::test_save_and_load_cache_round_trips PASSED   [ 36%]
tests/test_embed_cache.py::test_load_cache_missing_file_returns_empty PASSED [ 37%]
tests/test_embed_cache.py::test_missing_tags_returns_manifest_tags_not_in_cache PASSED [ 37%]
tests/test_embed_cache.py::test_sync_adds_only_missing_tags_and_persists PASSED [ 38%]
tests/test_embed_cache.py::test_sync_raises_on_missing_image_file PASSED [ 39%]
tests/test_explore_hub.py::test_render_html_lists_every_tool PASSED      [ 40%]
tests/test_generation_jobs.py::test_batch_splits_by_explore_fraction PASSED [ 41%]
tests/test_generation_jobs.py::test_fifty_fifty_split_matches_round_one_behavior PASSED [ 42%]
tests/test_generation_jobs.py::test_exploit_jobs_prefer_user_picks_over_elites PASSED [ 43%]
tests/test_generation_jobs.py::test_no_elites_and_no_picks_produces_only_explore_jobs PASSED [ 43%]
tests/test_lineage_view.py::test_compute_data_placeholder_when_no_parent_tags PASSED [ 44%]
tests/test_lineage_view.py::test_compute_data_builds_tree_when_parent_tags_exist PASSED [ 45%]
tests/test_live_cache.py::test_computes_once_and_caches_when_files_unchanged PASSED [ 46%]
tests/test_live_cache.py::test_recomputes_when_watched_file_mtime_changes PASSED [ 47%]
tests/test_live_cache.py::test_depends_on_passes_dependency_data_and_propagates_invalidation PASSED [ 48%]
tests/test_live_cache.py::test_concurrent_get_only_computes_once PASSED [ 49%]
tests/test_live_cache.py::test_get_reads_dependency_data_and_mtimes_from_a_single_snapshot PASSED [ 50%]
tests/test_manifest_index.py::test_index_by_tag_builds_lookup PASSED     [ 50%]
tests/test_manifest_index.py::test_item_summary_falls_back_to_basename_when_no_thumb PASSED [ 51%]
tests/test_manifest_index.py::test_item_summary_uses_thumb_when_present PASSED [ 52%]
tests/test_map_view.py::test_compute_data_reads_from_deps_not_disk PASSED [ 53%]
tests/test_map_view.py::test_render_html_embeds_points PASSED            [ 54%]
tests/test_migrate_picks_to_ratings.py::test_migrates_picks_not_already_rated PASSED [ 55%]
tests/test_migrate_picks_to_ratings.py::test_does_not_overwrite_an_existing_rating PASSED [ 56%]
tests/test_migrate_picks_to_ratings.py::test_leaves_existing_ratings_not_derived_from_picks_untouched PASSED [ 56%]
tests/test_novelty_decay.py::test_compute_data_builds_series_across_generations PASSED [ 57%]
tests/test_predicted_preference_pool.py::test_predicted_preference_pool_returns_empty_without_a_trained_model PASSED [ 58%]
tests/test_predicted_preference_pool.py::test_predicted_preference_pool_returns_empty_for_empty_manifest PASSED [ 59%]
tests/test_preference_model.py::test_build_training_set_uses_only_tags_present_in_both_embeddings_and_ratings PASSED [ 60%]
tests/test_preference_model.py::test_build_training_set_skips_unrecognized_labels PASSED [ 61%]
tests/test_preference_model.py::test_train_and_predict_proba_separates_obviously_different_clusters PASSED [ 62%]
tests/test_preference_model.py::test_cross_validate_returns_a_valid_accuracy_using_leave_one_out_below_min_labels PASSED [ 62%]
tests/test_preference_model.py::test_class_balance_error_flags_an_all_yes_label_set PASSED [ 63%]
tests/test_preference_model.py::test_class_balance_error_flags_an_all_no_label_set PASSED [ 64%]
tests/test_preference_model.py::test_class_balance_error_flags_a_minority_class_below_the_fold_count PASSED [ 65%]
tests/test_preference_model.py::test_class_balance_error_allows_a_well_balanced_label_set PASSED [ 66%]
tests/test_preference_model.py::test_class_balance_error_allows_an_imbalanced_but_above_fold_count_label_set_below_min_labels PASSED [ 67%]
tests/test_preference_model.py::test_main_writes_metadata_sidecar_on_successful_train PASSED [ 68%]
tests/test_preference_rank.py::test_build_ranked_items_sorts_descending_by_score PASSED [ 68%]
tests/test_preference_rank.py::test_build_ranked_items_respects_limit PASSED [ 69%]
tests/test_preference_rank.py::test_build_ranked_items_skips_tags_missing_from_manifest PASSED [ 70%]
tests/test_preference_rank_live.py::test_compute_data_returns_no_model_state_when_model_missing PASSED [ 71%]
tests/test_preference_settings.py::test_load_returns_false_default_when_file_missing PASSED [ 72%]
tests/test_preference_settings.py::test_save_then_load_round_trips_true PASSED [ 73%]
tests/test_preference_settings.py::test_save_writes_atomically_no_tmp_file_left_behind PASSED [ 74%]
tests/test_preference_settings.py::test_save_false_then_load_round_trips_false PASSED [ 75%]
tests/test_rate_page.py::test_render_html_includes_rate_api_calls PASSED [ 75%]
tests/test_rating_sampler.py::test_bin_manifest_splits_into_n_bins_by_bin_count PASSED [ 76%]
tests/test_rating_sampler.py::test_eligible_grid_excludes_reviewed_tags PASSED [ 77%]
tests/test_rating_sampler.py::test_pick_next_returns_none_when_everything_reviewed PASSED [ 78%]
tests/test_rating_sampler.py::test_pick_next_only_returns_eligible_items PASSED [ 79%]
tests/test_rating_sampler.py::test_pick_next_can_return_from_a_sparsely_populated_bin PASSED [ 80%]
tests/test_redundancy_view.py::test_compute_data_uses_similarity_scored_from_deps PASSED [ 81%]
tests/test_redundancy_view.py::test_render_html_embeds_edges PASSED      [ 81%]
tests/test_scan_gallery.py::test_compute_data_builds_items_with_similarity PASSED [ 82%]
tests/test_scan_gallery.py::test_render_html_embeds_data_and_infobtn_tips PASSED [ 83%]
tests/test_score_manifest.py::test_preprocess_and_constants_importable_from_new_location PASSED [ 84%]
tests/test_scoring.py::test_bin_edges_splits_sorted_values_into_n_groups PASSED [ 85%]
tests/test_scoring.py::test_bin_of_returns_last_bin_for_max_value PASSED [ 86%]
tests/test_scoring.py::test_bin_of_returns_first_bin_for_min_value PASSED [ 87%]
tests/test_scoring.py::test_novelty_from_similarity_inverts_similarity PASSED [ 87%]
tests/test_seed_browser.py::test_render_html_includes_seed_generation_ui PASSED [ 88%]
tests/test_seed_pool.py::test_merge_adds_new_subjects_and_reports_them PASSED [ 89%]
tests/test_seed_pool.py::test_merge_dedupes_case_insensitively PASSED    [ 90%]
tests/test_seed_pool.py::test_merge_dedupes_within_the_new_batch_itself PASSED [ 91%]
tests/test_seed_pool.py::test_load_missing_file_returns_empty_dict PASSED [ 92%]
tests/test_seed_pool.py::test_save_then_load_round_trips PASSED          [ 93%]
tests/test_similarity_index.py::test_compute_data_returns_tag_to_neighbors_mapping PASSED [ 93%]
tests/test_solution_map.py::test_compute_data_returns_both_outputs PASSED [ 94%]
tests/test_thumbnails.py::test_generate_thumbnail_produces_a_valid_small_jpeg PASSED [ 95%]
tests/test_thumbnails.py::test_generate_thumbnail_never_leaves_a_corrupt_file_at_dst_on_write_failure PASSED [ 96%]
tests/test_uncanny_gallery.py::test_compute_data_bins_manifest_without_importing_torch PASSED [ 97%]
tests/test_uncanny_gallery.py::test_render_html_produces_gallery_markup PASSED [ 98%]
tests/test_yes_rated_images.py::test_load_yes_rated_images_joins_ratings_against_manifest PASSED [ 99%]
tests/test_yes_rated_images.py::test_load_yes_rated_images_returns_empty_without_files PASSED [100%]

=============================== warnings summary ===============================
tests/test_preference_model.py: 17 warnings
  /workspace/trent-with-smart-prompts/.venv/lib/python3.14/site-packages/sklearn/linear_model/_logistic.py:451: OptimizeWarning: Unknown solver options: iprint
    opt_res = optimize.minimize(

tests/test_solution_map.py::test_compute_data_returns_both_outputs
  /workspace/trent-with-smart-prompts/.venv/lib/python3.14/site-packages/umap/umap_.py:1952: UserWarning: n_jobs value 1 overridden to 1 by setting random_state. Use no seed for parallelism.
    warn(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
====================== 116 passed, 18 warnings in 22.06s =======================
```

116/116 pass. No regressions, no new warnings.

## Em-dash / `-- ` check

`git diff --no-color | rg -n -e '—' -e ' -- '` returned no matches. The diff is clean.

## Commit

```
$ git log -1 --format='%H%n%an%n%ad%n%s'
61a4554b214164bdb639f1090ee2040c7321af41
jeremysball
Fri Jul 10 16:47:14 2026 -0400
feat(clawmarks): write preference model metadata sidecar on train
```

Conventional Commits format (`feat(clawmarks): ...`), exact message from the brief.

`git show --stat HEAD`:

```
$ git show --stat 61a4554
commit 61a4554b214164bdb639f1090ee2040c7321af41 (HEAD -> feat/preference-toggle)
Author: jeremysball
Date:   Fri Jul 10 16:47:14 2026 -0400

    feat(clawmarks): write preference model metadata sidecar on train

 src/clawmarks/search/preference_model.py |  19 +++++++++++++++++--
 tests/test_preference_model.py           |  35 +++++++++++++++++++++++++++++++
 2 files changed, 50 insertions(+), 1 deletion(-)
```

## Self-review notes

- I followed the brief's literal code for the new test, including its
  `# append to tests/test_preference_model.py` comment and the duplicate
  `import json` / `import numpy as np` lines (the existing top-of-file
  imports for `numpy as np` cover the new test, so the dupes are
  harmless; matching the brief verbatim was the priority per the
  instructions).
- The new test, the brief's prescribed failure mode (AttributeError on
  the `monkeypatch.setattr(... MODEL_META_FILE ...)` line), and the
  post-implementation test output all line up exactly. The new test
  also exercises a path the existing tests didn't: the first 60 lines
  of `main()` (load embeddings, load ratings, build training set, run
  cross-validation, train, write model, write meta). 116/116 pass, so
  no other test relied on `main()` not having side effects.
- The atomic tmp-then-`os.replace` write pattern matches the
  `preference_settings.py` `save()` pattern established in Task 1, so
  a future status page can read the sidecar without locking around
  partial writes. This is the kind of consistency that makes
  downstream code (Task 4's `build/preference_status.py`) safe by
  default, which is the whole point of writing this sidecar.
- The commit doesn't touch any data directory under `notes/`. The
  `git status` showed an untracked `notes/uncanny_seedrun1/` directory
  that I left alone (out of scope, and the project guidance is to be
  very careful with anything under `notes/`).
- `cv_accuracy` is rounded to 4 decimal places as the brief specifies.
  This is finer than the 3-decimal-place accuracy printed to stdout,
  which is the right choice for a machine-readable sidecar that a
  future status page will probably show as a percentage.

## Concerns

- None blocking. One minor observation for the orchestrator: the
  brief's prescribed `model` variable name in the test (e.g.
  `monkeypatch.setattr(preference_model, "MODEL_META_FILE", ...)`)
  relies on `import preference_model` having already happened earlier
  in the test file. That import is on line 3 of the existing test
  file, so the test works as written; just flagging it so the
  reviewer can confirm this is the same `preference_model` instance
  both tests are mutating (it is — same module, same import).
- The full `PYTHONPATH=src uv run pytest tests/ -v` run took 22
  seconds; if subsequent tasks in this plan also want a full-suite
  regression check, that adds up. Task 4 should follow the same
  pattern as the brief specifies for the targeted file
  (`tests/test_preference_model.py -v` for that file's own tests,
  full suite for final confidence).
