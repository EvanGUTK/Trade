let version = "0.0.1"

let ping _params =
  Ok (`Assoc [ ("pong", `Bool true); ("version", `String version) ])

let dispatch (req : Protocol.request) =
  match req.meth with
  | "ping" -> ping req.params
  | meth ->
      Error
        (Protocol.error Protocol.Method_not_found ("method not found: " ^ meth))

let is_blank line = String.equal (String.trim line) ""

let handle_line line =
  if is_blank line then None
  else
    match Protocol.parse_request line with
    | Error (id, err) ->
        Some (Protocol.to_line (Protocol.error_response ~id err))
    | Ok req -> (
        let outcome =
          try dispatch req
          with e ->
            Error
              (Protocol.error Protocol.Internal_error
                 ("internal error: " ^ Printexc.to_string e))
        in
        match req.id with
        | None -> None
        | Some id -> (
            match outcome with
            | Ok result ->
                Some (Protocol.to_line (Protocol.result_response ~id result))
            | Error err ->
                Some (Protocol.to_line (Protocol.error_response ~id err))))
