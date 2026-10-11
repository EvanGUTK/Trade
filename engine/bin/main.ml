(* trade_engine: newline-delimited JSON-RPC 2.0 over stdin/stdout.

   stdout carries protocol lines and nothing else. Every reply is flushed as
   soon as it is written because the gateway waits for it. Logs go to stderr. *)

let log fmt =
  Printf.kfprintf
    (fun oc ->
      output_char oc '\n';
      flush oc)
    stderr fmt

let rec serve () =
  match In_channel.input_line stdin with
  | None -> ()
  | Some line ->
      (match Trade_engine.Rpc.handle_line line with
      | Some reply ->
          print_string reply;
          print_char '\n';
          flush stdout
      | None -> ());
      serve ()

let () =
  log "trade_engine %s ready" Trade_engine.Rpc.version;
  (try serve () with Sys_error msg -> log "stdio closed: %s" msg);
  log "trade_engine exiting"
