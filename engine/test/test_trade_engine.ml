let () =
  Alcotest.run "trade_engine"
    [ ("money", Test_money.tests); ("rpc", Test_rpc.tests) ]
