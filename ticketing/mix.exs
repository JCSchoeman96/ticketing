defmodule Ticketing.MixProject do
  use Mix.Project

  def project do
    [
      app: :ticketing,
      version: "0.1.0",
      elixir: "~> 1.20.4",
      usage_rules: usage_rules(),
      elixirc_paths: elixirc_paths(Mix.env()),
      start_permanent: Mix.env() == :prod,
      aliases: aliases(),
      deps: deps(),
      dialyzer: [plt_add_apps: [:mix, :ex_unit]],
      compilers: [:phoenix_live_view] ++ Mix.compilers(),
      listeners: [Phoenix.CodeReloader],
      consolidate_protocols: Mix.env() != :dev
    ]
  end

  # Configuration for the OTP application.
  #
  # Type `mix help compile.app` for more information.
  def application do
    [
      mod: {Ticketing.Application, []},
      extra_applications: [:logger, :runtime_tools]
    ]
  end

  def cli do
    [
      preferred_envs: [
        {:check, :test},
        {:"check.types", :test},
        {:precommit, :test}
      ]
    ]
  end

  # Specifies which paths to compile per environment.
  defp elixirc_paths(:test), do: ["lib", "test/support"]
  defp elixirc_paths(_), do: ["lib"]

  # Specifies your project dependencies.
  #
  # Type `mix help deps` for examples and options.
  defp deps do
    [
      {:tidewave, "~> 0.9.1", only: :dev},
      {:usage_rules, ">= 1.2.8 and < 2.0.0", only: [:dev, :test]},
      {:ash, "~> 3.37.2"},
      {:ash_phoenix, "~> 2.3.25"},
      {:ash_postgres, "~> 2.15.2"},
      {:simple_sat, "~> 0.1.4"},
      {:igniter, "~> 0.8.4", only: [:dev, :test]},
      {:phoenix, "~> 1.8.15"},
      {:phoenix_ecto, "~> 4.5"},
      {:ecto_sql, "~> 3.13"},
      {:postgrex, "~> 0.22.4"},
      {:phoenix_html, "~> 4.1"},
      {:phoenix_live_reload, "~> 1.2", only: :dev},
      {:phoenix_live_view, "~> 1.2.12"},
      {:lazy_html, ">= 0.1.0", only: :test},
      {:phoenix_live_dashboard, "~> 0.8.3"},
      {:credo, "~> 1.7.19", only: [:dev, :test], runtime: false},
      {:sobelow, "~> 0.16.0", only: [:dev, :test], runtime: false},
      {:dialyxir, "~> 1.4.8", only: [:dev, :test], runtime: false},
      {:esbuild, "~> 0.10.0", runtime: Mix.env() == :dev},
      {:tailwind, "~> 0.5.1", runtime: Mix.env() == :dev},
      {:heroicons,
       github: "tailwindlabs/heroicons",
       tag: "v2.2.0",
       sparse: "optimized",
       app: false,
       compile: false,
       depth: 1},
      {:swoosh, "~> 1.16"},
      {:req, "~> 0.5"},
      {:telemetry_metrics, "~> 1.0"},
      {:telemetry_poller, "~> 1.0"},
      {:gettext, "~> 1.0"},
      {:jason, "~> 1.2"},
      {:dns_cluster, "~> 0.2.0"},
      {:bandit, ">= 1.14.0 and < 2.0.0-0"}
    ]
  end

  defp usage_rules do
    [
      file: "AGENTS.md",
      usage_rules: [],
      skills: [
        location: "../.agents/skills",
        build: [
          "ash-framework": [
            description:
              "Use when implementing or reviewing Ash resources, Ash Domains, actions, policies, validations, changes, preparations, calculations, aggregates, relationships, authorization, AshPostgres persistence, Ash errors, generators, code generation, or migrations.",
            usage_rules: [:ash, ~r/^ash_/]
          ],
          "phoenix-framework": [
            description:
              "Use when implementing or reviewing Phoenix or LiveView code, including components, controllers, routers, plugs, endpoints, channels, request handling, and web boundaries.",
            usage_rules: [:phoenix, ~r/^phoenix_/]
          ],
          "elixir-otp": [
            description:
              "Use for material Elixir/OTP process work involving GenServer, Supervisor, Task, process ownership, message passing, Registry, ETS, OTP lifecycle, supervision trees, or concurrency/process behavior. Do not load for routine resource CRUD.",
            usage_rules: [{:elixir, main: false}, {:otp, main: false}]
          ]
        ]
      ]
    ]
  end

  # Aliases are shortcuts or tasks specific to the current project.
  # For example, to install project dependencies and perform other setup tasks, run:
  #
  #     $ mix setup
  #
  # See the documentation for `Mix` for more info on aliases.
  defp aliases do
    [
      setup: [
        "deps.get",
        "ticketing.test_database.guard",
        "ecto.migrate -r Ticketing.MigrationRepo",
        "ticketing.db.grant_runtime_privileges",
        "run priv/repo/seeds.exs",
        "assets.setup",
        "assets.build"
      ],
      "ecto.setup": [
        "ticketing.test_database.guard",
        "ecto.create -r Ticketing.MigrationRepo",
        "ecto.migrate -r Ticketing.MigrationRepo",
        "ticketing.db.grant_runtime_privileges",
        "run priv/repo/seeds.exs"
      ],
      test: [
        "ticketing.test_database.guard",
        "ecto.create -r Ticketing.MigrationRepo --quiet",
        "ecto.migrate -r Ticketing.MigrationRepo --quiet",
        "ticketing.db.grant_runtime_privileges",
        "test"
      ],
      "assets.setup": ["tailwind.install --if-missing", "esbuild.install --if-missing"],
      "assets.build": ["compile", "tailwind ticketing", "esbuild ticketing"],
      "assets.deploy": [
        "tailwind ticketing --minify",
        "esbuild ticketing --minify",
        "phx.digest"
      ],
      check: [
        "cmd env MIX_ENV=dev mix usage_rules.sync --check",
        "hex.audit",
        "format --check-formatted",
        "compile --warnings-as-errors",
        "ash.codegen --check",
        "contract.authority",
        "test",
        "credo --strict",
        "sobelow --private --exit Medium",
        "cmd env MIX_ENV=dev mix assets.build"
      ],
      "check.types": ["dialyzer --format short"],
      precommit: [
        "cmd env MIX_ENV=dev mix usage_rules.sync --check",
        "format --check-formatted",
        "compile --warnings-as-errors",
        "test"
      ]
    ]
  end
end
