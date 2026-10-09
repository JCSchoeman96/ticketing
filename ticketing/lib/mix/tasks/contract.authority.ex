defmodule Mix.Tasks.Contract.Authority do
  use Mix.Task

  @shortdoc "Verify the pinned canonical contracts checkout"

  @impl Mix.Task
  def run(args) do
    Mix.Task.run("app.config")

    {options, _, invalid} = OptionParser.parse(args, strict: [pin_only: :boolean])

    if invalid != [] do
      Mix.raise("unknown contract.authority options: #{inspect(invalid)}")
    end

    pin_path = Path.expand("../../../../contracts/authority.json", __DIR__)

    with {:ok, pin} <- Ticketing.ContractAuthority.load_pin(pin_path) do
      if options[:pin_only] do
        Mix.shell().info("Contract authority schema valid (offline pin check)")
        Mix.shell().info("Repository: #{pin["repository"]}")
        Mix.shell().info("Reviewed commit: #{pin["reviewed_commit"]}")
        Mix.shell().info("CANON-1: #{pin["canon_version"]}")
      else
        checkout_path = Ticketing.ContractAuthority.default_checkout_path()

        case Ticketing.ContractAuthority.verify_checkout(checkout_path, pin) do
          {:ok, result} ->
            Mix.shell().info("Contract authority verified")
            Mix.shell().info("Repository: #{pin["repository"]}")
            Mix.shell().info("Path: #{result.path}")
            Mix.shell().info("Commit: #{result.commit}")
            Mix.shell().info("CANON-1: #{result.canon_version}")

          {:error, message} ->
            Mix.raise(message)
        end
      end
    else
      {:error, message} -> Mix.raise(message)
    end
  end
end
