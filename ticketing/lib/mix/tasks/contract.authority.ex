defmodule Mix.Tasks.Contract.Authority do
  use Mix.Task

  @shortdoc "Verify canonical authority stored in this repository"

  @impl Mix.Task
  def run(args) do
    Mix.Task.run("app.config")

    if args != [] do
      Mix.raise("mix contract.authority does not accept arguments")
    end

    case Ticketing.ContractAuthority.verify() do
      {:ok, result} ->
        Mix.shell().info("In-repository canonical authority verified")
        Mix.shell().info("Authority: #{result.path}")
        Mix.shell().info("CANON-1: #{result.canon_version}")
        Mix.shell().info("Active tracer: #{result.active_tracer}")

      {:error, message} ->
        Mix.raise(message)
    end
  end
end
