/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("_pb_users_auth_")

  // update collection data
  unmarshal({
    "createRule": "@request.auth.role = \"service\" || @request.auth.role = \"super_admin\" || (@request.auth.role = \"institution_admin\" && @request.auth.institution_id = institution_id)",
    "deleteRule": "id = @request.auth.id || @request.auth.role = \"super_admin\" || (@request.auth.role = \"institution_admin\" && @request.auth.institution_id = institution_id)",
    "indexes": [
      "CREATE UNIQUE INDEX `idx_tokenKey__pb_users_auth_` ON `users` (`tokenKey`)",
      "CREATE UNIQUE INDEX `idx_F3l7spP92R` ON `users` (`username`)",
      "CREATE UNIQUE INDEX `idx_email__pb_users_auth_` ON `users` (`email`) WHERE `email` != ''",
      "CREATE INDEX `idx_prUOgmQ5ix` ON `users` (`institution_id`)"
    ],
    "listRule": "id = @request.auth.id || @request.auth.role = \"super_admin\" || (@request.auth.role = \"institution_admin\" && @request.auth.institution_id = institution_id)",
    "updateRule": "(id = @request.auth.id && @request.body.role:isset = false) || @request.auth.role = \"super_admin\" || (@request.auth.role = \"institution_admin\" && @request.auth.institution_id = institution_id)",
    "viewRule": "id = @request.auth.id || @request.auth.role = \"super_admin\" || (@request.auth.role = \"institution_admin\" && @request.auth.institution_id = institution_id)"
  }, collection)

  // add field
  collection.fields.addAt(13, new Field({
    "cascadeDelete": false,
    "collectionId": "pbc_2630615650",
    "hidden": false,
    "id": "relation272652678",
    "maxSelect": 1,
    "minSelect": 0,
    "name": "institution_id",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "relation"
  }))

  // update field
  collection.fields.addAt(7, new Field({
    "hidden": false,
    "id": "select1466534506",
    "maxSelect": 1,
    "name": "role",
    "presentable": false,
    "required": true,
    "system": false,
    "type": "select",
    "values": [
      "admin",
      "user",
      "generic",
      "service",
      "institution_admin",
      "super_admin"
    ]
  }))

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("_pb_users_auth_")

  // update collection data
  unmarshal({
    "createRule": "@request.auth.role = \"service\" || @request.auth.role = \"admin\"",
    "deleteRule": "id = @request.auth.id || @request.auth.role = \"admin\"",
    "indexes": [
      "CREATE UNIQUE INDEX `idx_tokenKey__pb_users_auth_` ON `users` (`tokenKey`)",
      "CREATE UNIQUE INDEX `idx_F3l7spP92R` ON `users` (`username`)",
      "CREATE UNIQUE INDEX `idx_email__pb_users_auth_` ON `users` (`email`) WHERE `email` != ''"
    ],
    "listRule": "id = @request.auth.id || @request.auth.role = \"admin\"",
    "updateRule": "(id = @request.auth.id && @request.body.role:isset = false) || @request.auth.role = \"admin\"",
    "viewRule": "id = @request.auth.id || @request.auth.role = \"admin\""
  }, collection)

  // remove field
  collection.fields.removeById("relation272652678")

  // update field
  collection.fields.addAt(7, new Field({
    "hidden": false,
    "id": "select1466534506",
    "maxSelect": 1,
    "name": "role",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "select",
    "values": [
      "admin",
      "user",
      "generic",
      "service"
    ]
  }))

  return app.save(collection)
})
