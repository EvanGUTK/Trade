(** JSON-RPC 2.0 codec for the newline-delimited stdio protocol
    (docs/ARCHITECTURE.md §3).

    This module only encodes and decodes envelopes. It performs no I/O and never
    raises: malformed input is reported as an {!error} so that {!Rpc} can answer
    with the matching JSON-RPC error object. *)

(** Error codes. The five JSON-RPC standard codes come first; the
    [-32000..-32099] block is reserved for the engine and allocated in
    [engine/CLAUDE.md] §5. Only the standard codes are emitted today; the engine
    codes are defined so that the allocation is fixed before the handlers that
    need them exist. *)
type code =
  | Parse_error  (** [-32700]: the line is not valid JSON. *)
  | Invalid_request  (** [-32600]: valid JSON but not a JSON-RPC 2.0 request. *)
  | Method_not_found  (** [-32601] *)
  | Invalid_params  (** [-32602] *)
  | Internal_error  (** [-32603]: an exception escaped a handler. *)
  | Invariant_violation
      (** [-32000]: a ledger invariant failed; the session is unusable. *)
  | Unknown_session  (** [-32001] *)
  | Session_exists  (** [-32002] *)
  | Unknown_order  (** [-32003] *)
  | Clock_regression  (** [-32004]: a bar older than the session clock. *)
  | Replay_failed
      (** [-32005]: the replay log could not be read or did not verify. *)
  | Invalid_amount
      (** [-32006]: a money or quantity field is not a 64-bit integer. *)

val int_of_code : code -> int
val code_of_int : int -> code option

type error = { code : code; message : string; data : Yojson.Safe.t option }

val error : ?data:Yojson.Safe.t -> code -> string -> error

type request = {
  id : Yojson.Safe.t option;
      (** Echoed back verbatim. A JSON string, integer, or [`Null]. *)
  meth : string;
  params : Yojson.Safe.t option;
      (** An object or an array when present, as the spec requires. *)
}
(** A decoded request. [id = None] marks a notification: no response is owed. *)

val parse_request : string -> (request, Yojson.Safe.t * error) result
(** Decode one line. On failure the first component is the [id] to answer with:
    the request's own id when it could be recovered, [`Null] otherwise. *)

val result_response : id:Yojson.Safe.t -> Yojson.Safe.t -> Yojson.Safe.t
val error_response : id:Yojson.Safe.t -> error -> Yojson.Safe.t
val notification : meth:string -> Yojson.Safe.t -> Yojson.Safe.t

val to_line : Yojson.Safe.t -> string
(** Compact single-line encoding without a trailing newline. [Yojson] escapes
    newlines inside strings, so one value is always exactly one line. *)
