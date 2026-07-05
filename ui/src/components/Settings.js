import React, { useState, useEffect } from 'react'
import { useQuery, useMutation } from '@apollo/client'
import { useSelector } from 'react-redux'
import { getActiveLibrary } from '../stores/libraries/selector'

import {
  Switch,
  Flex,
  Stack,
  FormLabel,
} from '@chakra-ui/react'

import Modal from './Modal'
import {
  SETTINGS_STYLE,
  SETTINGS_COLOR,
  SETTINGS_LOCATION,
  SETTINGS_OBJECT,
  SETTINGS_FACE,
  GET_SETTINGS,
} from '../graphql/settings'
import '../static/css/Settings.css'

export default function Settings() {
  const activeLibrary = useSelector(getActiveLibrary)
  const [settings, setSettings] = useSettings(activeLibrary)
  const availableSettings = [
    {
      key: 'watchPhotos',
      type: 'boolean',
      label: 'Watch folder for new photos',
    },
    {
      key: 'classificationColorEnabled',
      type: 'boolean',
      label: 'Run color analysis on photos',
    },
    {
      key: 'classificationLocationEnabled',
      type: 'boolean',
      label: 'Run location detection on photos',
    },
    {
      key: 'classificationFaceEnabled',
      type: 'boolean',
      label: 'Run face recognition on photos',
    },
    {
      key: 'classificationStyleEnabled',
      type: 'boolean',
      label: 'Run style classification on photos',
    },
    {
      key: 'classificationObjectEnabled',
      type: 'boolean',
      label: 'Run object detection on photos',
    },
  ]

  function toggleBooleanSetting(key) {
    let newSettings = { ...settings }
    newSettings[key] = !settings[key]
    setSettings(newSettings)
    switch (key) {
      case 'classificationStyleEnabled':
        settingUpdateStyle({
          variables: {
            classificationStyleEnabled: newSettings.classificationStyleEnabled,
            libraryId: activeLibrary?.id,
          },
        }).catch((e) => {})
        return key
      case 'classificationLocationEnabled':
        settingUpdateLocation({
          variables: {
            classificationLocationEnabled:
              newSettings.classificationLocationEnabled,
            libraryId: activeLibrary?.id,
          },
        }).catch((e) => {})
        return key
      case 'classificationObjectEnabled':
        settingUpdateObject({
          variables: {
            classificationObjectEnabled:
              newSettings.classificationObjectEnabled,
            libraryId: activeLibrary?.id,
          },
        }).catch((e) => {})
        return key
      case 'classificationColorEnabled':
        settingUpdateColor({
          variables: {
            classificationColorEnabled: newSettings.classificationColorEnabled,
            libraryId: activeLibrary?.id,
          },
        }).catch((e) => {})
        return key
      case 'classificationFaceEnabled':
        settingUpdateFace({
          variables: {
            classificationFaceEnabled: newSettings.classificationFaceEnabled,
            libraryId: activeLibrary?.id,
          },
        }).catch((e) => {})
        return key
      default:
        return null
    }
  }

  const [settingUpdateStyle] = useMutation(SETTINGS_STYLE)
  const [settingUpdateColor] = useMutation(SETTINGS_COLOR)
  const [settingUpdateLocation] = useMutation(SETTINGS_LOCATION)
  const [settingUpdateObject] = useMutation(SETTINGS_OBJECT)
  const [settingUpdateFace] = useMutation(SETTINGS_FACE)

  return (
    <Modal className="Settings" topAccent={true}>
      <h1 className="heading">Settings</h1>
      <h2 className="subHeading">{activeLibrary?.name}</h2>
      <Stack spacing={4}>
        {availableSettings.map((item, index) => {
          let field = null

          if (settings) {
            if (item.type === 'boolean') {
              field = (
                <Switch
                  key={index}
                  id={item.key + 'New'}
                  isChecked={settings[item.key]}
                  onChange={() => toggleBooleanSetting(item.key)}
                  variantColor="cyan"
                />
              )
            }
          }

          return (
            <Flex justify="space-between" key={item.key + item.type}>
              <FormLabel htmlFor={item.key}>{item.label}</FormLabel>
              {field}
            </Flex>
          )
        })}
      </Stack>
    </Modal>
  )
}

export const useSettings = (activeLibrary) => {
  const [existingSettings, setSettings] = useState({})
  const { loading, data, refetch } = useQuery(GET_SETTINGS, {
    variables: { libraryId: activeLibrary?.id },
  })

  useEffect(() => {
    if (activeLibrary && !loading) {
      refetch()
    }
  }, [activeLibrary, loading, refetch])

  useEffect(() => {
    if (!loading && data) {
      let setting = { ...data.librarySetting.library }
      setting.sourceDirs = data.librarySetting.sourceFolder
      setSettings(setting)
    }
  }, [data, loading])

  function setAndSaveSettings(newSettings) {
    setSettings(newSettings)
  }
  return [existingSettings, setAndSaveSettings]
}
