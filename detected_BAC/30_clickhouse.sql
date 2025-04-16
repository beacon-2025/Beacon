-- Login with the root user
CREATE TABLE x (y INT, z TEXT) ENGINE = MergeTree() ORDER BY y;

-- Login with user 'regular_user'
EXPLAIN QUERY TREE SELECT * FROM x;
/*
    ┌─explain───────────────────────────────────────────────────────────────┐
 1. │ QUERY id: 0                                                           │
 2. │   PROJECTION COLUMNS                                                  │
 3. │     y Int32                                                           │
 4. │     z String                                                          │
 5. │   PROJECTION                                                          │
 6. │     LIST id: 1, nodes: 2                                              │
 7. │       COLUMN id: 2, column_name: y, result_type: Int32, source_id: 3  │
 8. │       COLUMN id: 4, column_name: z, result_type: String, source_id: 3 │
 9. │   JOIN TREE                                                           │
10. │     TABLE id: 3, alias: __table1, table_name: default.x               │
    └───────────────────────────────────────────────────────────────────────┘
*/