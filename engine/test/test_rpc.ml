open Trade_engine
module U = Yojson.Safe.Util

let reply line =
  match Rpc.handle_line line with
  | Some s -> Yojson.Safe.from_string s
  | None -> Alcotest.fail ("expected a reply for: " ^ line)

let error_code r = U.(member "error" r |> member "code" |> to_int)

let ping () =
  let r = reply {|{"jsonrpc":"2.0","id":1,"method":"ping"}|} in
  Alcotest.(check string) "jsonrpc" "2.0" U.(member "jsonrpc" r |> to_string);
  Alcotest.(check int) "id echoed" 1 U.(member "id" r |> to_int);
  let result = U.member "result" r in
  Alcotest.(check bool) "pong" true U.(member "pong" result |> to_bool);
  Alcotest.(check string)
    "version" Rpc.version
    U.(member "version" result |> to_string);
  Alcotest.(check bool) "no error member" true (U.member "error" r = `Null)

let ping_exact_line () =
  (* The byte-exact reply the gateway contract documents. *)
  let expected =
    Printf.sprintf
      {|{"jsonrpc":"2.0","id":7,"result":{"pong":true,"version":"%s"}}|}
      Rpc.version
  in
  Alcotest.(check (option string))
    "line" (Some expected)
    (Rpc.handle_line {|{"jsonrpc":"2.0","id":7,"method":"ping","params":{}}|})

let string_id_echoed () =
  let r = reply {|{"jsonrpc":"2.0","id":"abc-1","method":"ping"}|} in
  Alcotest.(check string) "id" "abc-1" U.(member "id" r |> to_string)

let unknown_method () =
  let r = reply {|{"jsonrpc":"2.0","id":2,"method":"nope"}|} in
  Alcotest.(check int) "code" (-32601) (error_code r);
  Alcotest.(check int) "id echoed" 2 U.(member "id" r |> to_int);
  Alcotest.(check bool) "no result member" true (U.member "result" r = `Null)

let malformed_json () =
  let r = reply "{not json" in
  Alcotest.(check int) "code" (-32700) (error_code r);
  Alcotest.(check bool) "id null" true (U.member "id" r = `Null)

let invalid_request () =
  let check name line expected_id =
    let r = reply line in
    Alcotest.(check int) (name ^ " code") (-32600) (error_code r);
    Alcotest.(check bool) (name ^ " id") true (U.member "id" r = expected_id)
  in
  check "array" "[1,2]" `Null;
  check "scalar" "42" `Null;
  check "wrong version" {|{"jsonrpc":"1.0","id":1,"method":"ping"}|} (`Int 1);
  check "missing method" {|{"jsonrpc":"2.0","id":3}|} (`Int 3);
  check "method not a string" {|{"jsonrpc":"2.0","id":4,"method":5}|} (`Int 4);
  check "params scalar" {|{"jsonrpc":"2.0","id":5,"method":"ping","params":1}|}
    (`Int 5);
  check "object id" {|{"jsonrpc":"2.0","id":{},"method":"ping"}|} `Null

let no_reply_when_not_owed () =
  let none name line =
    Alcotest.(check (option string)) name None (Rpc.handle_line line)
  in
  none "notification" {|{"jsonrpc":"2.0","method":"ping"}|};
  none "notification unknown method" {|{"jsonrpc":"2.0","method":"nope"}|};
  none "empty line" "";
  none "whitespace and CR" "  \t\r"

let never_raises () =
  List.iter
    (fun line -> ignore (Rpc.handle_line line))
    [
      "\000";
      "\"unterminated";
      "{\"jsonrpc\":";
      String.make 100_000 '[';
      "null";
      "{}";
    ]

let tests =
  [
    Alcotest.test_case "ping" `Quick ping;
    Alcotest.test_case "ping exact line" `Quick ping_exact_line;
    Alcotest.test_case "string id echoed" `Quick string_id_echoed;
    Alcotest.test_case "unknown method -> -32601" `Quick unknown_method;
    Alcotest.test_case "malformed json -> -32700" `Quick malformed_json;
    Alcotest.test_case "invalid request -> -32600" `Quick invalid_request;
    Alcotest.test_case "no reply when not owed" `Quick no_reply_when_not_owed;
    Alcotest.test_case "never raises" `Quick never_raises;
  ]
