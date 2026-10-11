(** Request dispatch: one decoded {!Protocol.request} in, one JSON reply out.

    This is the only place where exceptions are allowed to end. Every handler
    runs under a catch-all that converts an escaped exception into a [-32603]
    error, so the engine process never dies because of a request. Everything
    below this module returns [result]. This module performs no I/O; the binary
    in [bin/main.ml] owns stdin and stdout. *)

val version : string
(** The protocol version reported by [ping]. Bump it with every protocol change
    and record the change in docs/ARCHITECTURE.md §3 in the same commit. *)

val dispatch : Protocol.request -> (Yojson.Safe.t, Protocol.error) result
(** Route a request to its handler. Methods today: [ping]. *)

val handle_line : string -> string option
(** The full pipeline for one stdin line: decode, dispatch, encode. Returns the
    reply line without its newline, or [None] when no reply is owed (the line is
    blank or a notification). Never raises. *)
