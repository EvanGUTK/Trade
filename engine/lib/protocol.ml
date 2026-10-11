type code =
  | Parse_error
  | Invalid_request
  | Method_not_found
  | Invalid_params
  | Internal_error
  | Invariant_violation
  | Unknown_session
  | Session_exists
  | Unknown_order
  | Clock_regression
  | Replay_failed
  | Invalid_amount

let int_of_code = function
  | Parse_error -> -32700
  | Invalid_request -> -32600
  | Method_not_found -> -32601
  | Invalid_params -> -32602
  | Internal_error -> -32603
  | Invariant_violation -> -32000
  | Unknown_session -> -32001
  | Session_exists -> -32002
  | Unknown_order -> -32003
  | Clock_regression -> -32004
  | Replay_failed -> -32005
  | Invalid_amount -> -32006

let all_codes =
  [
    Parse_error;
    Invalid_request;
    Method_not_found;
    Invalid_params;
    Internal_error;
    Invariant_violation;
    Unknown_session;
    Session_exists;
    Unknown_order;
    Clock_regression;
    Replay_failed;
    Invalid_amount;
  ]

let code_of_int n = List.find_opt (fun c -> int_of_code c = n) all_codes

type error = { code : code; message : string; data : Yojson.Safe.t option }

let error ?data code message = { code; message; data }

type request = {
  id : Yojson.Safe.t option;
  meth : string;
  params : Yojson.Safe.t option;
}

let valid_id = function
  | `Int _ | `Intlit _ | `String _ | `Null -> true
  | _ -> false

let parse_request line =
  match Yojson.Safe.from_string line with
  | exception Yojson.Json_error msg ->
      Error (`Null, error Parse_error ("parse error: " ^ msg))
  | exception e ->
      Error (`Null, error Parse_error ("parse error: " ^ Printexc.to_string e))
  | `Assoc fields -> (
      let id = List.assoc_opt "id" fields in
      let reply_id = match id with Some v when valid_id v -> v | _ -> `Null in
      let invalid msg = Error (reply_id, error Invalid_request msg) in
      match List.assoc_opt "jsonrpc" fields with
      | Some (`String "2.0") -> (
          match id with
          | Some v when not (valid_id v) ->
              invalid "id must be a string, an integer, or null"
          | _ -> (
              match List.assoc_opt "method" fields with
              | Some (`String meth) -> (
                  match List.assoc_opt "params" fields with
                  | None -> Ok { id; meth; params = None }
                  | Some (`Assoc _ | `List _) as params ->
                      Ok { id; meth; params }
                  | Some _ -> invalid "params must be an object or an array")
              | _ -> invalid "method must be a string"))
      | _ -> invalid "jsonrpc must be \"2.0\"")
  | _ -> Error (`Null, error Invalid_request "request must be a JSON object")

let result_response ~id result =
  `Assoc [ ("jsonrpc", `String "2.0"); ("id", id); ("result", result) ]

let error_response ~id err =
  let fields =
    [ ("code", `Int (int_of_code err.code)); ("message", `String err.message) ]
  in
  let fields =
    match err.data with None -> fields | Some d -> fields @ [ ("data", d) ]
  in
  `Assoc [ ("jsonrpc", `String "2.0"); ("id", id); ("error", `Assoc fields) ]

let notification ~meth params =
  `Assoc
    [ ("jsonrpc", `String "2.0"); ("method", `String meth); ("params", params) ]

let to_line json = Yojson.Safe.to_string ~std:true json
