import Config
config :ash, policies: [show_policy_breakdowns?: true]

# Configure your database
#
# The MIX_TEST_PARTITION environment variable can be used
# to provide built-in test partitioning in CI environment.
# Run `mix help test` for more information.
test_db_host = System.get_env("TICKETING_TEST_DB_HOST", "127.0.0.1")
test_db_port = String.to_integer(System.get_env("TICKETING_TEST_DB_PORT", "55433"))
test_db_user = System.get_env("TICKETING_TEST_DB_USER", "ticketing_test")
test_db_password = System.fetch_env!("TICKETING_TEST_DB_PASSWORD")
test_db_base = System.get_env("TICKETING_TEST_DB_NAME", "ticketing_test")
test_runtime_db_user = System.get_env("TICKETING_TEST_RUNTIME_DB_USER", "ticketing_test_runtime")
test_runtime_db_password = System.fetch_env!("TICKETING_TEST_RUNTIME_DB_PASSWORD")
test_migration_db_user = System.get_env("TICKETING_TEST_MIGRATION_DB_USER", test_db_user)

test_migration_db_password =
  System.get_env("TICKETING_TEST_MIGRATION_DB_PASSWORD", test_db_password)

test_db_partition = System.get_env("MIX_TEST_PARTITION", "")
test_db_name = test_db_base <> test_db_partition

if test_runtime_db_user == test_migration_db_user do
  raise ArgumentError,
        "TICKETING_TEST_RUNTIME_DB_USER and TICKETING_TEST_MIGRATION_DB_USER must be different"
end

if test_db_port == 55432 do
  raise ArgumentError, "TEST Repo cannot use the DEV PostgreSQL port 55432"
end

if test_db_name == "ticketing_dev" do
  raise ArgumentError, "TEST Repo cannot use the DEV database ticketing_dev"
end

if test_db_base != "ticketing_test" do
  raise ArgumentError, "TICKETING_TEST_DB_NAME must be exactly ticketing_test"
end

config :ticketing, Ticketing.Repo,
  hostname: test_db_host,
  port: test_db_port,
  username: test_runtime_db_user,
  password: test_runtime_db_password,
  database: test_db_name,
  pool: Ecto.Adapters.SQL.Sandbox,
  show_sensitive_data_on_connection_error: false,
  pool_size: 10

config :ticketing, Ticketing.MigrationRepo,
  hostname: test_db_host,
  port: test_db_port,
  username: test_migration_db_user,
  password: test_migration_db_password,
  database: test_db_name,
  priv: "priv/repo",
  show_sensitive_data_on_connection_error: false,
  pool_size: 2

# We don't run a server during test. If one is required,
# you can enable the server option below.
config :ticketing, TicketingWeb.Endpoint,
  http: [ip: {127, 0, 0, 1}, port: 4002],
  secret_key_base: "mWDJxg4pTqKtNptLuhto/8jXRwu4LFJAQ8ZuPlVqhLbBybXG/DtVaoBbDw+nzrru",
  server: false

# In test we don't send emails
config :ticketing, Ticketing.Mailer, adapter: Swoosh.Adapters.Test

# Disable swoosh api client as it is only required for production adapters
config :swoosh, :api_client, false

# Print only warnings and errors during test
config :logger, level: :warning

# Initialize plugs at runtime for faster test compilation
config :phoenix, :plug_init_mode, :runtime

# Enable helpful, but potentially expensive runtime checks
config :phoenix_live_view,
  enable_expensive_runtime_checks: true

# Sort query params output of verified routes for robust url comparisons
config :phoenix,
  sort_verified_routes_query_params: true
