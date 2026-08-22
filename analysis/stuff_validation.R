# Stuff+ validation and visualization (R).
#
# Two analyses that use R's strengths:
#  1. Year-over-year reliability: is Stuff+ a stable, repeatable pitcher
#     skill? We correlate each pitcher's 2023 Stuff+ with their 2024 Stuff+.
#     A high correlation means stuff is a real trait, not noise - which is
#     why front offices trust stuff-based metrics over volatile results.
#  2. A publication-quality pitch-movement chart in ggplot2.

library(dplyr)
library(ggplot2)

art <- "model/artifacts"

# ---- 1. Year-over-year Stuff+ reliability ----------------------------
season <- read.csv(file.path(art, "pitcher_season_stuff.csv"))

y2023 <- season %>% filter(game_year == 2023) %>%
  select(pitcher, stuff_2023 = stuff_plus)
y2024 <- season %>% filter(game_year == 2024) %>%
  select(pitcher, stuff_2024 = stuff_plus)

paired <- inner_join(y2023, y2024, by = "pitcher")

ct <- cor.test(paired$stuff_2023, paired$stuff_2024)
cat("\n=== Year-over-year Stuff+ reliability (2023 -> 2024) ===\n")
cat(sprintf("Pitchers with 100+ pitches both seasons: %d\n", nrow(paired)))
cat(sprintf("Correlation r = %.3f\n", ct$estimate))
cat(sprintf("95%% CI: [%.3f, %.3f]\n", ct$conf.int[1], ct$conf.int[2]))
cat(sprintf("p-value = %.2e\n", ct$p.value))
cat("Interpretation: a strong positive r means Stuff+ is a repeatable\n")
cat("pitcher skill, not season-to-season noise.\n")

# reliability scatter
dir.create("analysis/output", showWarnings = FALSE)
p_rel <- ggplot(paired, aes(stuff_2023, stuff_2024)) +
  geom_point(alpha = 0.4, color = "#BD3039") +   # Red Sox red
  geom_smooth(method = "lm", se = TRUE, color = "black") +
  labs(title = "Stuff+ is a repeatable skill",
       subtitle = sprintf("Year-over-year correlation r = %.3f (n = %d pitchers)",
                           ct$estimate, nrow(paired)),
       x = "2023 Stuff+", y = "2024 Stuff+") +
  theme_minimal(base_size = 13)
ggsave("analysis/output/stuff_reliability.png", p_rel, width = 7, height = 6, dpi = 150)
cat("\nsaved analysis/output/stuff_reliability.png\n")

# ---- 2. Pitch-movement chart -----------------------------------------
mv <- read.csv(file.path(art, "movement_sample.csv"))

p_mov <- ggplot(mv, aes(pfx_x_in, pfx_z_in, color = pitch_type)) +
  geom_point(alpha = 0.3, size = 0.6) +
  coord_fixed() +
  labs(title = "Pitch movement by type",
       subtitle = "Horizontal vs. vertical break (inches), 30k pitch sample",
       x = "Horizontal break (in)", y = "Vertical break (in)",
       color = "Pitch") +
  theme_minimal(base_size = 13)
ggsave("analysis/output/pitch_movement.png", p_mov, width = 8, height = 6, dpi = 150)
cat("saved analysis/output/pitch_movement.png\n")